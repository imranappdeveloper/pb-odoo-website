# -*- coding: utf-8 -*-

import base64
import re
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import UserError

class ShippingScheduleImportWizard(models.TransientModel):
    _name = 'shipping.schedule.import.wizard'
    _description = 'Shipping Schedule Excel Import Wizard'

    schedule_id = fields.Many2one('shipping.schedule', string='Target Schedule')
    file_data = fields.Binary(string='Excel File (.xls / .xlsx)', required=True)
    file_name = fields.Char(string='File Name')

    def _parse_cell_date(self, val, datemode, current_year=2026):
        """Parse Excel date serial numbers or date strings like '8/19-8/22' or '7/24'."""
        if not val:
            return None, None
            
        import xlrd
        if isinstance(val, (float, int)):
            if val > 1000:
                try:
                    dt = xlrd.xldate_as_datetime(val, datemode)
                    return dt.date(), None
                except Exception:
                    pass

        val_str = str(val).strip()
        if not val_str or val_str in ['-', 'SKIP', 'NO CALL', 'N/A']:
            return None, None

        # Parse date range e.g. "8/19-8/22" or "08/19-08/22"
        m_range = re.match(r'(\d{1,2})/(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})', val_str)
        if m_range:
            m1, d1, m2, d2 = map(int, m_range.groups())
            dt1 = datetime(current_year, m1, d1).date()
            dt2 = datetime(current_year, m2, d2).date()
            return dt1, dt2

        # Parse single date string e.g. "7/24"
        m_single = re.match(r'(\d{1,2})/(\d{1,2})', val_str)
        if m_single:
            m1, d1 = map(int, m_single.groups())
            return datetime(current_year, m1, d1).date(), None

        return None, None

    def _parse_excel_content(self, file_bytes):
        """Full Excel parser for Header metadata and Multi-Region Port Call lines."""
        import xlrd

        try:
            workbook = xlrd.open_workbook(file_contents=file_bytes)
        except Exception as e:
            raise UserError(f'Failed to open Excel file: {str(e)}')

        # Find schedule sheet
        sheet = None
        for sname in workbook.sheet_names():
            if 'ecc' in sname.lower() or 'schedule' in sname.lower():
                sheet = workbook.sheet_by_name(sname)
                break
        if not sheet:
            sheet = workbook.sheet_by_index(0)

        carrier_name = 'Keihin Co., Ltd.'
        vessel_main = 'ARABIAN SEA'
        voyage_main = 'V.IE603'
        revision_no = 'REV00'

        # 1. Header Metadata Extraction
        for r in range(min(15, sheet.nrows)):
            row_vals = [str(sheet.cell_value(r, c)).strip() for c in range(sheet.ncols)]
            row_str = " ".join(row_vals).upper()

            if 'HOEGH' in row_str:
                carrier_name = 'Hoegh Autoliners'
            elif 'KEIHIN' in row_str:
                carrier_name = 'Keihin Co., Ltd.'

            rev_match = re.search(r'REV\.?\s*(\d+)', row_str)
            if rev_match:
                revision_no = f"REV{int(rev_match.group(1)):02d}"

            c1 = str(sheet.cell_value(r, 1)).strip().upper() if sheet.ncols > 1 else ''
            c3 = str(sheet.cell_value(r, 3)).strip() if sheet.ncols > 3 else ''
            if c1 == 'VESSEL' and c3:
                vessel_main = c3
            if c3.startswith('V.') or c3.startswith('VOY'):
                voyage_main = c3

        # 2. Parse Region Blocks
        # Block definitions: (default_region_name, label_col, val_col, start_row, end_row)
        block_configs = [
            ('East Africa', 1, 3, 8, 29),
            ('Sri Lanka', 14, 16, 8, 29),
            ('South America', 1, 3, 30, 46)
        ]

        regions_parsed = []

        for reg_name, l_col, v_col, s_row, e_row in block_configs:
            if s_row >= sheet.nrows:
                continue

            header_label = str(sheet.cell_value(s_row, l_col)).strip() if sheet.ncols > l_col else ''
            if header_label and len(header_label) > 3:
                trade_lane = header_label.replace('\n', ' ').strip()
            else:
                trade_lane = reg_name

            lines = []
            current_section = None
            seq = 10

            for r in range(s_row, min(e_row, sheet.nrows)):
                p_label = str(sheet.cell_value(r, l_col)).strip() if sheet.ncols > l_col else ''
                p_val = sheet.cell_value(r, v_col) if sheet.ncols > v_col else None
                p_val_str = str(p_val).strip().upper()

                if not p_label:
                    continue

                if p_label.lower() == 'origin':
                    current_section = 'pol'
                    continue
                elif p_label.lower() == 'destination':
                    current_section = 'pod'
                    continue

                if p_label.startswith('①') or 'CONTACT' in p_label.upper() or p_label.lower() == 'vessel':
                    continue
                if 'CARGO' in p_label.upper() or 'WEIGHT' in p_label.upper():
                    continue

                if current_section and p_label:
                    d1, d2 = self._parse_cell_date(p_val, workbook.datemode)
                    status = 'skipped' if p_val_str in ['SKIP', '-'] else 'scheduled'

                    lines.append({
                        'sequence': seq,
                        'call_type': current_section,
                        'port_name': p_label.upper(),
                        'port_code': p_label[:5].upper().replace(' ', ''),
                        'eta': d1 if current_section == 'pod' else None,
                        'etd': d1 if current_section == 'pol' else None,
                        'eta_end': d2 if current_section == 'pod' else None,
                        'etd_end': d2 if current_section == 'pol' else None,
                        'status': status,
                        'remarks': f"Imported from {self.file_name or 'Excel'}"
                    })
                    seq += 10

            if lines:
                regions_parsed.append({
                    'carrier_name': carrier_name,
                    'vessel_name': vessel_main,
                    'voyage_no': voyage_main,
                    'revision_no': revision_no,
                    'trade_lane': trade_lane,
                    'lines': lines
                })

        return regions_parsed

    def action_import(self):
        """1-click import multi-region schedules from Excel file."""
        self.ensure_one()
        if not self.file_data:
            raise UserError('Please select an Excel file to upload.')

        excel_bytes = base64.b64decode(self.file_data)
        regions = self._parse_excel_content(excel_bytes)

        if not regions:
            raise UserError('No valid schedule data found in Excel file.')

        created_schedules = self.env['shipping.schedule']

        for reg in regions:
            c_name = reg['carrier_name']
            v_name = reg['vessel_name']
            voy_no = reg['voyage_no']
            rev_no = reg['revision_no']
            lane = reg['trade_lane']

            # Find or Create Schedule Header per Trade Lane
            schedule = self.env['shipping.schedule'].search([
                ('carrier_name', '=ilike', c_name),
                ('vessel_name', '=ilike', v_name),
                ('voyage_no', '=', voy_no),
                ('trade_lane', '=ilike', lane)
            ], limit=1)

            if schedule:
                schedule.write({
                    'revision_no': rev_no,
                    'issue_date': fields.Date.today()
                })
            else:
                schedule = self.env['shipping.schedule'].create({
                    'carrier_name': c_name,
                    'vessel_name': v_name,
                    'voyage_no': voy_no,
                    'revision_no': rev_no,
                    'trade_lane': lane,
                    'issue_date': fields.Date.today(),
                    'cargo_restrictions': 'Prohibits pure EV/Hydrogen. Allows Hybrid/PHEV. Requires NKKK/SK for tank trucks.'
                })

            # Replace Port Call Lines
            schedule.line_ids.unlink()

            lines_to_create = []
            for line in reg['lines']:
                lines_to_create.append({
                    'schedule_id': schedule.id,
                    'sequence': line['sequence'],
                    'call_type': line['call_type'],
                    'port_name': line['port_name'],
                    'port_code': line['port_code'],
                    'eta': line['eta'],
                    'etd': line['etd'],
                    'eta_end': line['eta_end'],
                    'etd_end': line['etd_end'],
                    'status': line['status'],
                    'remarks': line['remarks'],
                })

            if lines_to_create:
                self.env['shipping.schedule.line'].create(lines_to_create)

            created_schedules |= schedule

        return {
            'type': 'ir.actions.act_window',
            'name': 'Shipping Schedules',
            'res_model': 'shipping.schedule',
            'domain': [('id', 'in', created_schedules.ids)],
            'view_mode': 'list,form',
            'target': 'current',
        }

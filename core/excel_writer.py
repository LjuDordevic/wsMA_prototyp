import openpyxl 

def write_to_excel(data, output_path):
    wb = openpyxl.Workbook()
    ws = wb.active

    headers = ['test file', 'input', 'output', \
               'source_keyword_wo_glob', 'source_keyword_w_glob',\
                'osource_keyword', 'rource_keyword', 'orource_keyword', \
                    'sum_all_source', 'option_env', 'new_lines_bc_of_def_', \
                        'new_lines_bc_of_glob', 'new_lines_bc_cd', 'new_lines_bc_named_choice', \
                            'removed_bc_orsource', 'removed_lines_bc_cd', 'removed_lines_bc_named_choice',\
                                'removed_optional_choice_attr', 'removed_bool_choice_attr', 'removed_tristate_choice_attr']
    ws.append(headers)

    for row_data in data:
        ws.append([row_data.get(h, '') for h in headers])
    
    wb.save(output_path)
    print(f"Excel saved: {output_path}")
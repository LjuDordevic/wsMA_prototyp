import openpyxl 

def write_to_excel(data, output_path):
    wb = openpyxl.Workbook()
    ws = wb.active

    headers = ['test file', 'input', 'output', 'source_keyword', 'osource_keyword', 'rource_keyword', 'orource_keyword', 'new lines bc source', 'new lines bc cd']
    ws.append(headers)

    for row_data in data:
        ws.append([row_data.get(h, '') for h in headers])
    
    wb.save(output_path)
    print(f"Excel saved: {output_path}")
#!/usr/bin/env python3
import urllib.request
import re
import csv
import os
from html import unescape

def map_row(prod_title, header, row_cells):
    # Map raw row cells into [Product, Version, GA, EOM, EOL] based on header column names
    version = ""
    ga = ""
    eom = ""
    eol = ""
    
    # We inspect the header to find the indices of each target field
    for idx, col in enumerate(header):
        if idx >= len(row_cells):
            break
        col_lower = col.lower()
        val = row_cells[idx]
        
        # 1. Version / Service Pack
        if any(term in col_lower for term in ('version', 'release', 'pack', 'admin', 'host')):
            if not version:
                version = val
            else:
                version = f"{version} - {val}" if val else version
        # 2. GA / FCS Date
        elif any(term in col_lower for term in ('ga', 'fcs', 'availability')):
            ga = val
        # 3. EOM / General Support Ends / ESPOS Ends / Full Support
        elif any(term in col_lower for term in ('eom', 'general', 'espos', 'full support')):
            eom = val
        # 4. EOL / LTSS / LTS / Support Ends / Maintenance End / Core Ends
        elif any(term in col_lower for term in ('eol', 'end of life', 'ltss', 'lts', 'support ends', 'maintenance support')):
            if eol:
                eol = f"{eol} / {val}" if val else eol
            else:
                eol = val
                
    # If version is still empty, let's use the first cell
    if not version and row_cells:
        version = row_cells[0]
    # If ga is still empty and we have at least 2 cells, let's use the second cell
    if not ga and len(row_cells) > 1:
        ga = row_cells[1]
        
    # Let's clean up any leading/trailing slashes or formatting remnants
    if eol.startswith(" / "):
        eol = eol[3:]
    if eol.endswith(" / "):
        eol = eol[:-3]
        
    return [prod_title, version, ga, eom, eol]

def main():
    # 1. Fetch the webpage
    url = "https://www.suse.com/lifecycle"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    print(f"Fetching {url}...")
    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching the lifecycle page: {e}")
        return
    
    # 2. Find all product rows in the main table
    # Pattern to match the main product rows: <tr class="row" id="X" ...>
    product_pattern = re.compile(
        r'<tr[^>]*class="row"[^>]*id="([^"]+)"[^>]*data-title="([^"]+)"[^>]*data-url="([^"]+)"[^>]*>',
        re.IGNORECASE
    )
    
    products = product_pattern.findall(html)
    print(f"Found {len(products)} products to process.")
    
    output_rows = []
    
    for idx, (prod_id, prod_title, prod_url) in enumerate(products):
        prod_title_clean = prod_title.strip()
        
        # Determine the boundaries of the detail section for this product
        detail_tag = f'id="detail{prod_id}"'
        detail_start = html.find(detail_tag)
        if detail_start == -1:
            # Symmetrical skip for products that aren't expandable
            continue
            
        # Sibling row boundary
        if idx + 1 < len(products):
            next_prod_id, _, _ = products[idx + 1]
            boundary = html.find(f'id="{next_prod_id}"', detail_start)
        else:
            boundary = html.find('</tbody>', detail_start)
            
        if boundary == -1:
            boundary = len(html)
            
        block = html[detail_start:boundary]
        
        # Check if there is a nested table inside this block
        if '<table>' not in block.lower():
            continue
            
        # Extract table block
        table_start = block.lower().find('<table>')
        table_end = block.lower().find('</table>')
        table_block = block[table_start:table_end + 8]
        
        # Parse all table rows (<tr>...</tr>)
        tr_pattern = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL | re.IGNORECASE)
        trs = tr_pattern.findall(table_block)
        
        # First, find the header row of this table to guide mapping
        header = None
        cell_pattern = re.compile(r'<t[dh][^>]*>(.*?)</t[dh]>', re.DOTALL | re.IGNORECASE)
        
        for tr in trs:
            cells = cell_pattern.findall(tr)
            if not cells:
                continue
                
            cleaned_cells = []
            for cell in cells:
                cleaned = re.sub(r'<[^>]+>', '', cell)
                cleaned = unescape(cleaned)
                cleaned = cleaned.replace('\xa0', ' ')
                cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                cleaned_cells.append(cleaned)
                
            if cleaned_cells:
                first_cell = cleaned_cells[0].lower()
                # Check if this row is a header
                if '<th' in tr.lower() or first_cell in ('version', 'releases', 'service pack release', 'product release', 'supported host os', 'product'):
                    header = cleaned_cells
                    break
                    
        if not header:
            # Fallback default header if none detected
            header = ['Version', 'GA', 'EOM', 'EOL']
            
        # Now, parse and map all the data rows
        for tr in trs:
            # Skip if contains <th>
            if '<th' in tr.lower():
                continue
                
            cells = cell_pattern.findall(tr)
            if not cells:
                continue
                
            cleaned_cells = []
            for cell in cells:
                cleaned = re.sub(r'<[^>]+>', '', cell)
                cleaned = unescape(cleaned)
                cleaned = cleaned.replace('\xa0', ' ')
                cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                if cleaned in ('', '-', '—'):
                    cleaned = ''
                cleaned_cells.append(cleaned)
                
            if cleaned_cells and any(cleaned_cells):
                first_cell = cleaned_cells[0].lower()
                # Skip header rows
                if first_cell in ('version', 'releases', 'service pack release', 'product release', 'supported host os', 'product'):
                    continue
                    
                # Map using the found header
                mapped = map_row(prod_title_clean, header, cleaned_cells)
                output_rows.append(mapped)
                
    # Write to a single combined CSV file
    csv_file = "suse_lifecycle_data.csv"
    try:
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(output_rows)
        print(f"\nSuccessfully wrote {len(output_rows)} total mapped lifecycle entries to {os.path.abspath(csv_file)}")
    except Exception as e:
        print(f"Error writing CSV file: {e}")

if __name__ == '__main__':
    main()

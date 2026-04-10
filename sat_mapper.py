import xml.etree.ElementTree as ET
import csv

def create_mapping_csv(xml_file, output_csv):
    """
    Parses satellites.xml and creates a CSV mapping file.
    Format: name, pos (e.g. 45.0W for -450, 10.0E for 100)
    """
    try:
        # Load and parse the XML file
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Prepare to write to CSV
        with open(output_csv, mode='w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            # Write header
            writer.writerow(['name', 'pos'])
            
            # Iterate through each <sat> tag in the XML
            for sat in root.findall('sat'):
                name = sat.get('name')
                raw_position = int(sat.get('position'))
                
                # Convert position (e.g., -450 -> 45.0W, 100 -> 10.0E)
                # Absolute value / 10 gives the decimal degree
                deg = abs(raw_position) / 10.0
                direction = 'W' if raw_position < 0 else 'E'
                pos_formatted = f"{deg}{direction}"
                
                # Write entry to CSV
                writer.writerow([name, pos_formatted])
                
        print(f"Successfully created {output_csv}")

    except FileNotFoundError:
        print(f"Error: The file '{xml_file}' was not found.")
    except ET.ParseError:
        print(f"Error: Failed to parse '{xml_file}'. Ensure it is a valid XML.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# Permanent Instruction: include summary mapping logic
if __name__ == "__main__":
    # Specify your input and output filenames
    input_file = 'satellites.xml'
    output_file = 'mapping.csv'
    
    create_mapping_csv(input_file, output_file)

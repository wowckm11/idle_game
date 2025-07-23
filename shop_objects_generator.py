import csv

def generate_shop_objects_csv():
    """
    Generates a CSV file named 'shop_objects.csv' with predefined game item data.
    """
    data = [
        # Header row
        ["category", "name", "image", "cost", "timeout", "income", "heat_generation", "max_heat", "conductivity"],
        # Data rows
        ["shop_logo", "uranium_rod", "uranium_rod", "10", "15", "1", "1", "5", "1"],
        ["shop_logo", "yellow_rod", "yellow_rod", "20", "20", "4", "4", "20", "2"],
        ["shop_logo", "red_rod", "red_rod", "50", "25", "5", "8", "40", "4"],
        ["shop_logo", "blue_rod", "blue_rod", "250", "30", "16", "16", "80", "8"],
        ["systems_logo", "heat_sink", "heat_sink", "25", "0", "0", "0", "300", "0.1"],
        ["systems_logo", "pipe", "pipe", "25", "0", "0", "0", "30", "2"],
        ["systems_logo", "pipe", "pipe", "25", "0", "0", "0", "120", "8"],
        ["systems_logo", "pipe", "pipe", "25", "0", "0", "0", "240", "16"],
        ["systems_logo", "pipe", "pipe", "25", "0", "0", "0", "480", "32"],
        ["systems_logo", "lvl1_cooling", "lvl1_cooling", "25", "0", "0", "-0.025", "0", "0"]
    ]

    file_name = "shop_objects_generated.csv"
    with open(file_name, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerows(data)

    print(f"File '{file_name}' generated successfully with the specified content.")

if __name__ == "__main__":
    generate_shop_objects_csv()

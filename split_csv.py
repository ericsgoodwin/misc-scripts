import csv
import os


def split_csv(input_file, output_dir, base_name, chunk_size=50000):
    os.makedirs(output_dir, exist_ok=True)
    with open(input_file, mode="r", newline="", encoding="utf-8") as infile:
        reader = csv.reader(infile)
        header=next(reader)

        file_count = 1
        row_count = 0

        # construct the path for the first output file
        out_path = os.path.join(output_dir, f"{base_name}_{file_count}.csv")
        outfile = open(out_path, mode="w", newline="", encoding="utf-8")
        writer = csv.writer(outfile)

        # Write the header to the first file
        writer.writerow(header)

        for row in reader:
            if row_count >= chunk_size:
                # Close the current file and start a new one with header
                outfile.close()
                file_count += 1
                row_count = 0
                out_path = os.path.join(output_dir, f"{base_name}_{file_count}.csv")
                outfile = open(out_path, mode="w", newline="", encoding="utf-8")
                writer = csv.writer(outfile)
                writer.writerow(header)
            writer.writerow(row)
            row_count += 1
    print(f"CSV file split into {file_count} files in '{output_dir}'.")

def main():
    input_file = input("input_file:")
    output_dir = input("output_dir:")
    base_name = input("Base name:")

    split_csv(input_file, output_dir, base_name)


if __name__ == '__main__':
    main()
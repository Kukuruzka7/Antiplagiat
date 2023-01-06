def parse_arguments():
    import argparse
    parser = argparse.ArgumentParser(description='process args')
    parser.add_argument('input_file', metavar='input_file', type=argparse.FileType('r'),
                        help='input file with pairs of files to compare')
    parser.add_argument('output_file', metavar='output_file', type=argparse.FileType('w'),
                        help='output file to which to write the result')
    args = vars(parser.parse_args())
    return args['input_file'], args['output_file']


def normalize():
    return None


def compare(name1: str, name2: str) -> float:
    try:
        file1 = open(name1)
        file2 = open(name2)
    except IOError:
        return -1.0
    else:
        with file1, file2:
            return 0.0


if __name__ == '__main__':
    input_file, output_file = parse_arguments()
    try:
        for line in input_file:
            file_name1, file_name2 = line.split()
            result = compare(file_name1, file_name2)
            if result == -1.0:
                output_file.write("Problems with code-files\n")
            else:
                output_file.write(f"{result}\n")
    finally:
        input_file.close()
        output_file.close()

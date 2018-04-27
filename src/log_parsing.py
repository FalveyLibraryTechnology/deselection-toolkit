import datetime

def parse_request(row):
    request = {}
    lines = row[4].split('\n')
    l_index = 0
    # Get faculty name
    faculty_name = ""
    while lines[l_index] != 'Faculty First Name:':
        l_index += 1
    faculty_name = lines[l_index + 1]

    while lines[l_index] != 'Faculty Last Name:':
        l_index += 1
    faculty_name += ' ' + lines[l_index + 1]

    # Make new faculty member
    while lines[l_index] != 'Faculty Department:':
        l_index += 1
    department = lines[l_index + 1]

    while lines[l_index] != 'Campus Address:':
        l_index += 1
    address = lines[l_index + 1]

    request["faculty"] = {
        "name": faculty_name,
        "department": department,
        "address": address
    }

    # Get request id
    request["date"] = datetime.datetime.strptime(row[0], "%b %d, %Y, %I:%M:%S %p")

    request["books"] = []
    parts = row[4].split("Barcode:\n")
    book_submissions = parts[1:]
    first_barcode = True
    for bt in book_submissions:
        bc = 0
        blines = bt.split('\n')
        barcode = blines[0].strip()

        while blines[bc] != 'Destination:':
            bc += 1
        personal = blines[bc + 1].strip() == 'Patron'

        while blines[bc] != 'Comment:':
            bc += 1
        comment = '\n'.join(blines[bc + 1:]).strip()

        request["books"].append({
            "barcode": barcode,
            "personal": personal,
            "comment": comment
        })

    return request

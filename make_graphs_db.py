
from graphs import bar_graph, box_chart, pie_chart

def label_graph(filename, department_bars, month):
    department_labels = []
    for bar in department_bars:
        name = bar[3]
        p1 = 100 * bar[1] / bar[0]
        p2 = 100 * bar[2] / bar[0]
        label = name
        if p1 > 0 or p2 > 0:
            label += "\n"
        if p1 > 0:
            label += "%.1f%%" % p1
            if p2 > 0:
                label += "/"
        if p2 > 0:
            label += "%.1f%%" % p2
        department_labels.append(label)
    bar_graph(
        "reports/%s/%s.png" % (month, filename),
        [bar[:3] for bar in department_bars],
        key=["Total Marked", "Total Retained", "Retained for Personal"],
        labels=department_labels,
        title=month
    )

def create_department_graph(weeding_barcodes, books, month):
    department_counts = {}
    for barcode in weeding_barcodes:
        dept_match = re.search('^([A-Z]+)', weeding_data_books[barcode]["callnumber"])
        department = dept_match.group(1)
        if not department in department_counts:
            department_counts[department] = {
                "name": department,
                "total": 0,
                "retain": 0,
                "personal": 0,
            }
        department_counts[department]["total"] += 1

    for record in books:
        dept_match = re.search('^([A-Z]+)', record["callnumber"])
        department = dept_match.group(1)
        if not department in department_counts:
            print ("Wrong Month: %s (%s)" % (record["barcode"], department))
        else:
            department_counts[department]["retain"] += 1
            if record["for_personal"]:
                department_counts[department]["personal"] += 1

    department_bars = []
    for department in department_counts:
        department_bars.append([
            department_counts[department]["total"],
            department_counts[department]["retain"],
            department_counts[department]["personal"],
            department_counts[department]["name"],
        ])

    department_bars.sort(key=lambda x: x[3], reverse=False)
    label_graph("callnumber_areas_by_callnumber", department_bars, month)

    department_bars.sort(key=lambda x: x[0], reverse=True)
    label_graph("callnumber_areas_by_size", department_bars, month)

    department_bars.sort(key=lambda x: x[1], reverse=True)
    label_graph("callnumber_areas_by_retention", department_bars, month)

    # department_bars.sort(key=lambda x: x[1] / x[0], reverse=True)
    # label_graph("callnumber_areas_by_retention_percent", department_bars, month)

def create_faculty_graph(books, month):
    books.sort(key=lambda b: b["faculty"])

    faculty = {}
    for record in books:
        if not record["faculty"] in faculty:
            faculty[record["faculty"]] = {
                "total": 0,
                "personal": 0,
            }
        faculty[record["faculty"]]["total"] += 1
        if record["for_personal"]:
            faculty[record["faculty"]]["personal"] += 1

    sorted_faculty = []
    for name in faculty:
        sorted_faculty.append({
            "name": all_faculty[name]["name"],
            "department": all_faculty[name]["department"],
            "books": faculty[name]["total"],
            "personal": faculty[name]["personal"],
        })
    sorted_faculty.sort(key=lambda f: f["books"], reverse=True)

    faculty_bars = []
    faculty_labels = []
    for f in sorted_faculty:
        faculty_labels.append("%s\n%s" % (f["name"].replace(" ", " \n"), f["department"].split(" ")[0]))
        faculty_bars.append([
            f["books"],
            f["personal"],
        ])
    bar_graph(
        "reports/%s/faculty.png" % month, faculty_bars,
        key=["Total Retained", "Retained for Personal"],
        labels=faculty_labels,
        title=month
    )

def callnumber_breakdowns(folder):
    global all_effective, weeding_data_books

    department_counts = {}
    for barcode in weeding_data_books:
        dept_match = re.search('^([A-Z]+)', weeding_data_books[barcode]["callnumber"])
        department = dept_match.group(1)
        if not department in department_counts:
            department_counts[department] = {
                "name": department,
                "total": 0,
                "retain": 0,
                "personal": 0,
            }
        department_counts[department]["total"] += 1
    for barcode in all_effective:
        dept_match = re.search('^([A-Z]+)', weeding_data_books[barcode]["callnumber"])
        department = dept_match.group(1)
        record = all_effective[barcode]
        if record["for_personal"]:
            department_counts[department]["personal"] += 1
        else:
            department_counts[department]["retain"] += 1

    gg_recommendations = {}
    collection_totals = {}
    with open_workbook("adjustments/GreenGlass Project Overview.xlsx") as gg_report:
        sheet = gg_report.sheet_by_index(0)
        for r in range(2, sheet.nrows):
            rvalues = [str(x).strip() for x in sheet.row_values(r)]
            if len(rvalues) < 7 or len(rvalues[0]) == 0:
                continue
            callnumber = rvalues[0]
            if callnumber[:11] == "Exception: ":
                callnumber = callnumber[11:]
            if len(callnumber) > 2:
                callnumber = callnumber[:2]
            gg_withdrawl = int(float(rvalues[6])) if len(rvalues[6]) > 0 else 0 # Matches
            c_total = int(float(rvalues[5])) if len(rvalues[5]) > 0 else 0      # Total
            if callnumber in department_counts:
                if not callnumber in gg_recommendations:
                    if c_total > 0:
                        collection_totals[callnumber] = c_total
                        gg_recommendations[callnumber] = gg_withdrawl
                else:
                    collection_totals[callnumber] += c_total
                    gg_recommendations[callnumber] += gg_withdrawl

    with open("stacked_data.csv", "w", newline="") as csvfile:
        fieldnames = [
            "Callnumber",
            # "Book Total",
            # "GreenGlass Recommendations",
            "Exempt from review after quantitative analysis",
            "Retained based on qualitative analysis",
            "Donated to Better World Books",
            "Retained At Faculty Request",
            "Retained to Personal Collection"
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for key in collection_totals:
            writer.writerow({
                fieldnames[0]: key,
                # fieldnames[1]: collection_totals[key],
                fieldnames[1]: max(0, collection_totals[key] - gg_recommendations[key] - department_counts[key]["total"]),
                fieldnames[2]: max(0, gg_recommendations[key] - department_counts[key]["total"]),
                fieldnames[3]: max(0, department_counts[key]["total"] - department_counts[key]["retain"] - department_counts[key]["personal"]),
                fieldnames[4]: department_counts[key]["retain"],
                fieldnames[5]: department_counts[key]["personal"],
            })
    data_folder = "reports/%s/pies_data" % folder
    if not os.path.exists(data_folder):
        os.mkdir(data_folder)
    for cn in collection_totals:
        if collection_totals[cn] > 0:
            exempt = max(0, collection_totals[cn] - gg_recommendations[cn])
            retain_qual = max(0, gg_recommendations[cn] - department_counts[cn]["total"])
            donated = max(0, department_counts[cn]["total"] - department_counts[cn]["retain"] - department_counts[cn]["personal"])

            with open(data_folder + "/%s.csv" % cn, "w") as csvfile:
                csvfile.write("%s,%%,#\n" % cn)
                csvfile.write("Exempt from review after quantitative analysis,%f,%d\n" % (exempt / collection_totals[cn], exempt))
                csvfile.write("Retained based on qualitative analysis,%f,%d\n" % (retain_qual / collection_totals[cn], retain_qual))
                csvfile.write("Retained based on faculty feedback,%f,%d\n" % (department_counts[cn]["retain"] / collection_totals[cn], department_counts[cn]["retain"]))
                csvfile.write("Donated to faculty on request,%f,%d\n" % (department_counts[cn]["personal"] / collection_totals[cn], department_counts[cn]["personal"]))
                csvfile.write("Donated to Better World Books,%f,%d\n" % (donated / collection_totals[cn], donated))
                csvfile.write("Total books,1,%d\n" % collection_totals[cn])
    '''
    box_folder = "reports/%s/box_charts" % folder
    full_folder = "reports/%s/pies_full" % folder
    stacked_folder = "reports/%s/pies_stacked" % folder

    if not os.path.exists(box_folder):
        os.mkdir(box_folder)
    if not os.path.exists(full_folder):
        os.mkdir(full_folder)
    if not os.path.exists(stacked_folder):
        os.mkdir(stacked_folder)

    bar = ProgressBar(len(collection_totals.keys()))
    for cn in collection_totals:
        # print ("%s: %s / %s (%s / %s)" % (
        #     cn.rjust(2),
        #     str(gg_recommendations[cn]).rjust(4),
        #     str(collection_totals[cn]).ljust(6),
        #     str(department_counts[cn]["retain"] + department_counts[cn]["personal"]).rjust(4),
        #     str(department_counts[cn]["total"]).ljust(4),
        # ))
        if collection_totals[cn] > 0:
            exempt = max(0, collection_totals[cn] - gg_recommendations[cn])
            retain_qual = max(0, gg_recommendations[cn] - department_counts[cn]["total"])
            donated = max(0, department_counts[cn]["total"] - department_counts[cn]["retain"] - department_counts[cn]["personal"])

            with open(data_folder + "/%s.csv" % cn, "w") as csvfile:
                csvfile.write("%s,%%,#\n" % cn)
                csvfile.write("Exempt from review after quantitative analysis,%f,%d\n" % (exempt / collection_totals[cn], exempt))
                csvfile.write("Retained based on qualitative analysis,%f,%d\n" % (retain_qual / collection_totals[cn], retain_qual))
                csvfile.write("Retained based on faculty feedback,%f,%d\n" % (department_counts[cn]["retain"] / collection_totals[cn], department_counts[cn]["retain"]))
                csvfile.write("Donated to faculty on request,%f,%d\n" % (department_counts[cn]["personal"] / collection_totals[cn], department_counts[cn]["personal"]))
                csvfile.write("Donated to Better World Books,%f,%d\n" % (donated / collection_totals[cn], donated))
                csvfile.write("Total books,1,%d\n" % collection_totals[cn])

            pie_chart(stacked_folder + "/%s_stacked.png" % cn, {
                "total": collection_totals[cn],
                "title": cn,
                "arcs": [
                    {
                        "level": 0,
                        "value": collection_totals[cn],
                        "color": (148, 156, 166), # grey
                        "label": "Total Books\n%s" % comma(collection_totals[cn]),
                    },
                    {
                        "level": 0,
                        "value": gg_recommendations[cn],
                        "color": (193, 205,  35), # green
                        "label": "Qualitative Analysis\n%s - %.2f%%" % (
                            comma(gg_recommendations[cn]),
                            100 * gg_recommendations[cn] / collection_totals[cn]
                        ),
                    },
                    {
                        "level": 1,
                        "value": department_counts[cn]["retain"],
                        "color": (248, 151,  40), # orange
                        "label": "Retained By Request\n%s - %.2f%%" % (
                            comma(department_counts[cn]["retain"]),
                            100 * department_counts[cn]["retain"] / collection_totals[cn]
                        ),
                    },
                    {
                        "level": 1,
                        "value": department_counts[cn]["personal"],
                        "color": (255, 220,  79), # yellow
                        "label": "Donated to Faculty\n%s - %.2f%%" % (
                            comma(department_counts[cn]["personal"]),
                            100 * department_counts[cn]["personal"] / collection_totals[cn]
                        ),
                    },
                    {
                        "level": 1,
                        "value": donated,
                        "color": ( 80, 145, 205), # blue
                        "label": "Donated to Better World\n%s - %.2f%%" % (
                            comma(donated),
                            100 * donated / collection_totals[cn]
                        ),
                    },
                ],
            })

            pie_chart(full_folder + "/%s_full.png" % cn, {
                "total": collection_totals[cn],
                "title": cn,
                "arcs": [
                    {
                        "level": 0,
                        "value": exempt,
                        "color": (  0, 112, 192), # blue
                        "label": "Exempt via\nquantitative analysis\n%s - %.2f%%" % (
                            comma(exempt),
                            100 * exempt / collection_totals[cn]
                        ),
                    },
                    {
                        "level": 0,
                        "value": retain_qual,
                        "color": (255, 255,   0), # yellow
                        "label": "Retained via\nqualitative analysis\n%s - %.2f%%" % (
                            comma(retain_qual),
                            100 * retain_qual / collection_totals[cn]
                        ),
                    },
                    {
                        "level": 0,
                        "value": department_counts[cn]["retain"],
                        "color": (255,   0,   0), # red
                        "label": "Retained based\non Feedback\n%s - %.2f%%" % (
                            comma(department_counts[cn]["retain"]),
                            100 * department_counts[cn]["retain"] / collection_totals[cn]
                        ),
                    },
                    {
                        "level": 0,
                        "value": department_counts[cn]["personal"],
                        "color": ( 84, 130,  53), # dark green
                        "label": "Donated to Faculty\n%s - %.2f%%" % (
                            comma(department_counts[cn]["personal"]),
                            100 * department_counts[cn]["personal"] / collection_totals[cn]
                        ),
                    },
                    {
                        "level": 0,
                        "value": donated,
                        "color": (146, 208,  80), # green
                        "label": "Donated to Better World\n%s - %.2f%%" % (
                            comma(donated),
                            100 * donated / collection_totals[cn]
                        ),
                    },
                ],
            })

            retain_label  = "Retained based on feedback\n(%s - %.2f%%)" % (
                                comma(department_counts[cn]["retain"]),
                                100 * department_counts[cn]["retain"] / collection_totals[cn]
                            )
            to_faculty_label  = "Donated to Faculty\n(%s - %.2f%%)" % (
                                    comma(department_counts[cn]["personal"]),
                                    100 * department_counts[cn]["personal"] / collection_totals[cn]
                                )
            donated_label = "Donated to Better World\n(%s - %.2f%%)" % (
                                comma(donated),
                                100 * donated / collection_totals[cn]
                            )
            box_chart(box_folder + "/%s_box.png" % cn, {
                "total": collection_totals[cn],
                "key": [
                        { "color": (248, 151,  40), "label": retain_label },
                        { "color": (  0, 146, 143), "label": to_faculty_label },
                        { "color": (193, 205,  35), "label": donated_label },
                ],
                "values": [
                    [
                        { "value": department_counts[cn]["retain"], "color": (248, 151,  40), "label": retain_label.replace("\n", " ") },
                        { "value": department_counts[cn]["personal"], "color": (  0, 146, 143), "label": to_faculty_label.replace("\n", " ") },
                        { "value": donated, "color": (193, 205,  35), "label": donated_label.replace("\n", " ") },
                    ],
                    [
                        { "value": retain_qual, "color": ( 80, 145, 205), "label": "Retained via qualitative analysis (%s - %.2f%%)" % (
                            comma(retain_qual),
                            100 * retain_qual / collection_totals[cn]
                        )}
                    ],
                    [
                        { "value": exempt, "color": (255, 210,  79), "label": "Exempt from review after quantitative analysis (%s - %.2f%%)" % (
                            comma(exempt),
                            100 * exempt / collection_totals[cn]
                        )}
                    ],
                ]
            })
        bar.progress()
    bar.finish()
    '''
    return {
        "greenglass": gg_recommendations,
        "book_totals": collection_totals,
        "department_counts": department_counts
    }

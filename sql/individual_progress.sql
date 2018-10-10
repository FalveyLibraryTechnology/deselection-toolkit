DROP TABLE IF EXISTS posted_counts;

CREATE TEMPORARY TABLE posted_counts AS 
	SELECT librarian_assignments.librarian_id as librarian_id, COUNT(posted_books.barcode) as counts 
		FROM posted_books 
		INNER JOIN librarian_assignments ON librarian_assignments.cn_section = posted_books.cn_section
		GROUP BY librarian_assignments.librarian_id;

SELECT librarians.name as "NAME", 
	(100.0 * SUM(callnumber_sections.reviewed_count)) / SUM(callnumber_sections.gg_recommended) as "EST. PERCENT REVIEWED",
	posted_counts.counts as "NUMBER OF BOOKS POSTED",
	SUM(callnumber_sections.reviewed_count) as "EST. REVIEWED", 
	SUM(callnumber_sections.gg_recommended) as "GG RECOMMENDED", 
	SUM(callnumber_sections.collection_count) as "TOTAL COLLECTION COUNT",
	COUNT(callnumber_sections.cn_section) as "# OF SECTIONS ASSIGNED",
	GROUP_CONCAT(callnumber_sections.cn_section, ", ") as "ASSIGNED SECTIONS"
	FROM callnumber_sections
	INNER JOIN librarian_assignments ON librarian_assignments.cn_section = callnumber_sections.cn_section
	INNER JOIN librarians ON librarians.librarian_id = librarian_assignments.librarian_id
	INNER JOIN posted_counts ON posted_counts.librarian_id = librarians.librarian_id
	GROUP BY librarians.name
	ORDER BY librarians.name
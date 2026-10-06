# Homework template contract

Reference: `/tmp/hw3-homework-template.docx`, SHA256
`fbaa32ec1280231827a314eb95ac7c6b5ad55f4c5ffc5b8d666d3b867b486763`.
One portrait A4 section, one rendered reference page. Margins L/R/T 0.79 inches,
B 1.18 inches. Reference render `/tmp/hw3-template-render/page-1.png`;
style evidence `/tmp/hw3-template-style.json`. No tables or images.

Design authority is the retained DOCX, including direct run formatting,
numbered instructions, title, body styles, blank paragraphs, and footer page
number. Preserve all package parts except `word/document.xml` byte for byte.
Keep paragraph and run properties unchanged, editing only text in selected slots.
Allow additional pagination when application description and task text expand.

Slot map uses zero-based `word/document.xml/w:document/w:body/w:p` indexes:
2 assignment number; 5 name and ID; 16 recording URL (pending); 18 repository
URL; 20 application name; 22 description below half a page; 26 actual prompt
and pending screenshot evidence. Preserve all other paragraphs and structures.
No fake URLs, screenshots, or claims of a live model demonstration.

# HumbleJson
Parser to extract the contents of a Humble Bundle campaign and print it in a simplified manner.

Takes the data from a JSON object containing all the elements in the Humble Bundle campaign, extracts the desired data and prints it.

Initial version:
- Prints to console: name, author, publisher and description of each item, ordered by tiers.

Usage:      
Paramenters: -h | -u "urls to parse" | -a | -o "output_dir" | -l "url to libgen"

Long parameters: help | urls="" | archive | out="" | libgen=""

- -u Input URLs. It can be a single URL or a list of comma separated URLs
- -a Flag to archive the Humble Bundle page into the Wayback Machine
- -o Output dir for the files from Library Genesis
- -l Base URL for the Libgen mirror
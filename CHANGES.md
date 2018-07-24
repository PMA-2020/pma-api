# v1.1.0, 25 July 2018
## New features
- Added dedicated docs, accessible at http://api-docs.pma2020.org

## General updates
- Default route now redirects to docs.
- Versioned to 1.1.0, "1.x" to keep consistent with the API route version 'v1', and "1.1.x" to not cause any confusion that this is "the initial release".

## Developer updates
- Added continuous integration
- Changed changelog to Markdown format.

# v0.1.9, 14 November 2017
- Group /datalab/data over time correctly if only one characteristic
- Better, more readable CSV downloads with other languages supported

# v0.1.8, 10 October 2017
- Fix characteristic group bug in /datalab/data
- Move precision to top level under 'chartOptions'
- All values returned after rounding
- Dataset update

# v0.1.7, 2 October 2017
- Empty CSV download is now a 204 server response
- Implemented server-side caching for /datalab/init
- Added query param cached=false to force dynamic response
- Various dataset fixes, including date MM-YYYY

# v0.1.6, 14 September 2017
- Send back datalab/init data for query parameters to /datalab/data
- Update documentation with overTime and format=csv

# v0.1.5, 13 September 2017
- Echo back query parameters for /datalab/data and
   /datalab/combos
- CSV download fixed
- Support /datalab/data?overTime=true
- Add in partner information with survey
- Change /datalab/combos so that it always returns three
   lists of what is valid to choose for the datalab

# v0.1.4, 11 September 2017
- Small documentation update
- 'label.id' used in /datalab/init result
- /datalab/data returns a list of series
- CSV format broken for now

# v0.1.3, 6 September 2017
- CSV format allowed on /v1/datalab/data?format=csv
- Support CORS
- Version information moved to /version
- Internal refactor to return custom object

# v0.1.2, 1 September 2017
- Datalab init for indicators fixed
- Added back '/' root route
- Added support for UI translations

# v0.1.1, 31 August 2017
- `/v1/version` route and JSON objects return metadata object
   which shows version information for code and source data files.
- datalab/init has better-formatted objects for indicator,
   characteristicGroup, and country-round select boxes.
- Added metadata table to database
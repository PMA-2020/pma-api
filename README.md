# PMA API
This is the PMA2020 API.

# Developer Documentation
This is the developer documentation.
## Common Endpoints
This is documentation for common API endpoints.

### Root `/`
This endpoint re-routes directly to: `/resources` 

### Resources `/resources`
#### Example 1 - No parameters
Example: `/resources`

Returns:  
A list of resources.
```
{
  "resources": [
    {
      "name": "countries", 
      "resource": "https://<base_url>/surveys"
    }, 
    {
      "name": "surveys", 
      "resource": "https://<base_url>/surveys"
    }, 
    {
      "name": "texts", 
      "resource": "https://<base_url>/texts"
    }, 
    {
      "name": "indicators", 
      "resource": "https://<base_url>/indicators"
    }, 
    {
      "name": "data", 
      "resource": "https://<base_url>/data"
    }, 
    {
      "name": "characteristicGroups", 
      "resource": "https://<base_url>/characteristicGroups"
    }
  ]
}
```

## Application Specific Endpoints
This is documentation for application specific endpoints, such as 
[PMA2020 Datalab](http://datalab.pma2020.org).

### Application initialization `/datalab/init`
Fetch data for all key resources in one request. This endpoint takes no 
query parameters.

Example: `/datalab/init`

Returns:  
A list of all specific, key resources (surveys, indicators, and 
characteristics), all of which have at least one stored data point associated.
```
{
    "indicators": [
        {
            "code": "<item>",
            "label_code": "<item>",
            "definition_code": "<item>",
            "order": "<item>",
            "level2_code": "<item>"
        },
        ...
    ],
    "characteristicGroups": [
        {
            "code": "<item>",
            "label_code": "<item>",
            "definition_code": "<item>",
            "order": "<item>",
            "category_code": "<item>"
        },
        ...
    ],	
    "characteristics": [
        {
            "code": "<item>",
            "label_code": "<item>",
            "order": "<item>"
        },
        ...
    ],
    "surveys": [
        {
            "code": "<item>",
            "label_code": "<item>",
            "order": "<item>",
            "country_label_code": "<item>",
            "geography_label_code": "<item>"
        },
        ...
    ],
    "strings": {
        "en": {
            "code": "<string>",
            ...
        },
        "fr": {
            "code": "<string>",
            ...
        },
		...
    }
    "languages": {
        "en": "English",
        "fr": "French"
        ...
    }
}
```

### Filtering by existing relational data `/datalab`
#### Example 1 - Filter by all key resources
Example: `/datalab`

Returns:  
A list of all specific, key resources (surveys, indicators, and 
characteristics), all of which have at least one stored data point associated.

#### Example 2 - Filter by surveys
Example: `/v1/datalab/combos?survey=GH2013PMA,GH2014PMA`

Returns:  
A list of indicator and characteristic combinations which have one or more 
stored data point associated with any of the provided surveys. From this list 
provided, the client application should have enough information to filter valid
data isaggregated further by specified indicator(s) and characteristic(s), 
without the need for any further API calls.
```
{
  "results": [
    {
      "characteristicGroup.id": "none", 
      "indicator.id": "mcpr_aw"
    }, 
    {
      "characteristicGroup.id": "residence", 
      "indicator.id": "mcpr_aw"
    }, 
    {
      "characteristicGroup.id": "wealth_quintile", 
      "indicator.id": "mcpr_aw"
    }, 
    ...
    }
  ], 
  "resultsSize": 6
}
```


#### Example 3 - Filter by indicators or characteristics
Example: `/datalab?[indicator | characteristic]=ID1`

Returns:  
A list of indicators or characteristics (whichever was not provided in the 
query) which have one or more stored data point associated, and a separate list
of surveys which have one or more stored data point associated. Note that these
are separate lists which are returned, as opposed to *example 2* where one list
of all valid combinations are returned.

### Querying Data `/datalab/data`
Query data. Accepts parameters: 'survey', 'indicator', and 'characteristic'.
#### Example 1 - Query all data needed to render a visualization 
Example: `/v1/datalab/data?survey=GH2013PMA,GH2014PMA&indicator=mcpr_aw&characteristicGroup=none`

Returns:  
A list of all data points filtered by parameters provided.
```
{
  "results": [
    {
      "characteristic.id": "none", 
      "characteristicGroup.id": "none", 
      "indicator.id": "mcpr_aw", 
      "precision": 1, 
      "survey.id": "GH2013PMA", 
      "value": 15.4
    }, 
    {
      "characteristic.id": "none", 
      "characteristicGroup.id": "none", 
      "indicator.id": "mcpr_aw", 
      "precision": null, 
      "survey.id": "GH2014PMA", 
      "value": 16.1
    }
  ], 
  "resultsSize": 2
}
```

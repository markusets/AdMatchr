# body_requests.py

def generate_report(start_date, end_date):
    return {
        "reportStart": start_date,
        "reportEnd": end_date,
        "orderByColumns": [
            {"column": "numberId", "direction": "desc"},
            {"column": "callDt", "direction": "desc"}
        ],
        "valueColumns": [
            {"column": "campaignName"},
            {"column": "publisherName"},
            {"column": "connectedCallLengthInSeconds"},
            {"column": "callDt"},
            {"column": "inboundPhoneNumber"},
            {"column": "number"},
            {"column": "numberId"},
            {"column": "conversionAmount"}
        ]
    }


# body_requests.py

def generate_ringba_insights(start_date, end_date):
    return {
        "reportStart": start_date,
        "reportEnd": end_date,
        "groupByColumns": [
            {
                "column": "campaignName",
                "displayName": "Campaign"
            },
            {
                "column": "tag:User:sub5"
            },
            {
                "column": "publisherName",
                "displayName": "Publisher"
            }
        ],
        "valueColumns": [
            {"column": "callCount", "aggregateFunction": None},
            {"column": "liveCallCount", "aggregateFunction": None},
            {"column": "endedCalls", "aggregateFunction": None},
            {"column": "connectedCallCount", "aggregateFunction": None},
            {"column": "payoutCount", "aggregateFunction": None},
            {"column": "convertedCalls", "aggregateFunction": None},
            {"column": "nonConnectedCallCount", "aggregateFunction": None},
            {"column": "duplicateCalls", "aggregateFunction": None},
            {"column": "blockedCalls", "aggregateFunction": None},
            {"column": "incompleteCalls", "aggregateFunction": None},
            {"column": "earningsPerCallGross", "aggregateFunction": None},
            {"column": "conversionAmount", "aggregateFunction": None},
            {"column": "payoutAmount", "aggregateFunction": None},
            {"column": "profitGross", "aggregateFunction": None},
            {"column": "profitMarginGross", "aggregateFunction": None},
            {"column": "convertedPercent", "aggregateFunction": None},
            {"column": "callLengthInSeconds", "aggregateFunction": None},
            {"column": "avgHandleTime", "aggregateFunction": None},
            {"column": "totalCost", "aggregateFunction": None}
        ],
        "orderByColumns": [
            {
                "column": "callCount",
                "direction": "desc"
            }
        ],
        "formatTimespans": True,
        "formatPercentages": True,
        "generateRollups": True,
        "maxResultsPerGroup": 1000,
        "filters": [
            {
                "anyConditionToMatch": [
                    {
                        "column": "campaignName",
                        "value": "DEBT - SPA - FB +15k - Affiliates",
                        "isNegativeMatch": True,
                        "comparisonType": "EQUALS"
                    }
                ]
            },
            {
                "anyConditionToMatch": [
                    {
                        "column": "tag:DialedNumber:Name",
                        "value": "MSN",
                        "isNegativeMatch": True,
                        "comparisonType": "CONTAINS"
                    }
                ]
            }
        ],
        "formatTimeZone": "America/New_York"
    }


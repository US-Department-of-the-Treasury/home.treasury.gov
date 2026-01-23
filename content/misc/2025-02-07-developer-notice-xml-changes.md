---
date: 2025-02-07
title: Developer Notice - XML changes
url: /developer-notice-xml-changes
draft: false
---

[Subscribe to Developer Notice updates](https://public.govdelivery.com/accounts/USTREAS/subscriber/new?topic_id=USTREAS_1153)

 

### ON FEBRUARY 18, 2025 THE XML FEEDS AND CSV WILL INCLUDE NEW ELEMENTS

Effective with the inaugural auction of the new benchmark 6-week Treasury bill, currently anticipated to take place on Tuesday, February 18, 2025, Treasury plans to include 6-week bill prices in its input data set for the daily yield curve. Treasury also plans to add a 1.5-month CMT to the Daily Treasury Par Yield Curve Rates and 6-week bill rates to the Daily Treasury Bill Rates that it publishes. The XML feeds will include new XML elements as follows:

#### Daily Treasury Par Yield Curve Rates

<d:BC_1_5MONTH m:type="Edm.Double"></d:BC_1_5MONTH>

#### Daily Treasury Bill Rates

<d:ROUND_B1_CLOSE_6WK_2 m:type="Edm.Double"></d:ROUND_B1_CLOSE_6WK_2><d:ROUND_B1_YIELD_6WK_2 m:type="Edm.Double"></d:ROUND_B1_YIELD_6WK_2><d:MATURITY_DATE_6WK m:type="Edm.DateTime"></d:MATURITY_DATE_6WK><d:CUSIP_6WK></d:CUSIP_6WK><d:CS_6WK_CLOSE_AVG m:type="Edm.Double"></d:CS_6WK_CLOSE_AVG><d:CS_6WK_YIELD_AVG m:type="Edm.Double"></d:CS_6WK_YIELD_AVG>

 

New fields for CSV will begin showing the evening of February 14 in preparation for the first auction, February 18.

 

### On October 19, 2022 the newly Updated XML Feeds and CSV will Include New Elements

Effective with the inaugural auction of the new benchmark 17-week Treasury bill, currently anticipated to take place on Wednesday, October 19, 2022, Treasury plans to include 17-week bill prices in its input data set for the daily yield curve. Treasury also plans to add a 4-month CMT to the Daily Treasury Par Yield Curve Rates and 17-week bill rates to the Daily Treasury Bill Rates that it publishes. The  XML feeds will include new XML elements as follows:

#### Daily Treasury Par Yield Curve Rates

<d:BC_4MONTH m:type="Edm.Double"></d:BC_4MONTH>

#### Daily Treasury Bill Rates

<d:ROUND_B1_CLOSE_17WK_2 m:type="Edm.Double"></d:ROUND_B1_CLOSE_17WK_2><d:ROUND_B1_YIELD_17WK_2 m:type="Edm.Double"></d:ROUND_B1_YIELD_17WK_2><d:MATURITY_DATE_17WK m:type="Edm.DateTime"></d:MATURITY_DATE_17WK><d:CUSIP_17WK></d:CUSIP_17WK><d:CS_17WK_CLOSE_AVG m:type="Edm.Double"></d:CS_17WK_CLOSE_AVG><d:CS_17WK_YIELD_AVG m:type="Edm.Double"></d:CS_17WK_YIELD_AVG>

 

New fields for CSV will begin showing the evening of October 18 in preparation for the first auction, October 19.

 

### Changes that took effect June 2, 2022 to the XML Feeds and and CSV Downloads for the "All" time period

On June 2, Treasury made the following changes for when the "All" period is selected in the “Select Time Period” dropdown for each of the five data sets. (Note: This update will not affect the views for any other time period.)

#### XML Feeds

The orange “XML” button and the text for “View the XML feed” were removed for the "All" time period. The XML data feed is no longer accessible in a browser, but the feed still exists for developers to access via API. The data feed changed to include pagination, but still returns all data of a given interest rate type for all time periods. To access the “All” XML data feed, developers can use the value “all” and a page number to access it. To loop through all pages, increment page number by one until there is no data inside the "<entry>" tag. Looping through years is possible by using the start year in the data in the “Data Availability” table below to loop through years to obtain a record of a specific time or for all time.

- ExamplesKEY = pageVALUE = XXX (number)https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=[value]&field_tdr_date_value=[all]&page=[xxx]https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value=all&page=24
- Data Availability
 

| Interest Rate Type | Available From |
| --- | --- |
| Daily Treasury Par Yield Curve Rates | 1990 |
| Daily Treasury Bill Rates | 2002 |
| Daily Treasury Long-Term Rates | 2000 |
| Daily Treasury Par Real Yield Curve Rates | 2003 |
| Daily Treasury Real Long-Term Rates | 2000 |

#### CSV Downloads

The orange “CSV” button and the text/link for “Download CSV” were removed. This was replaced by a link to “Download Interest Rates Data Archive (CSV Format)” that leads to a NEW page. On this page, historic CSV data is available in an archived format, so users can download static CSVs that contain a fixed range of years. This page contains the following information:

- Historical Daily Interest Rates data is available in comma-separated values (CSV) files that can be opened in programs like Microsoft Excel spreadsheets and notepad, and which can easily be imported into other applications.
 

| Time Period | Archive File as of June 2, 2022 |
| --- | --- |
| 1990-2021 | yield-curve-rates-1990-2021.csv |
| 2011-2020 | yield-curve-rates-2011-2020.csv |
| 2001-2010 | yield-curve-rates-2001-2010.csv |
| 1990-2000 | yield-curve-rates-1990-2000.csv |

 

| Time Period | Archive File as of June 2, 2022 |
| --- | --- |
| 2002-2021 | bill-rates-2002-2021.csv |
| 2011-2020 | bill-rates-2011-2020.csv |
| 2002-2010 | bill-rates-2002-2010.csv |

 

| Time Period | Archive File as of June 2, 2022 |
| --- | --- |
| 2000-2021 | long-term-rates-2000-2021.csv |
| 2011-2020 | long-term-rates-2011-2020.csv |
| 2000-2010 | long-term-rates-2000-2010.csv |

 

| Time Period | Archive File as of June 2, 2022 |
| --- | --- |
| 2003-2021 | par-real-yield-curve-rates-2003-2021.csv |
| 2011-2020 | par-real-yield-curve-rates-2011-2020.csv |
| 2003-2010 | par-real-yield-curve-rates-2003-2010.csv |

 

| Time Period | Archive File as of June 2, 2022 |
| --- | --- |
| 2000-2021 | real-long-term-rates-2000-2021.csv |
| 2011-2020 | long-term-rates-2011-2020.csv |
| 2000-2010 | long-term-rates-2000-2010.csv |

 

### Changes That tooK effect February 4, 2022

**Notice to those with APIs and/or services that consume the Treasury Interest Rate Statistics XML data: **Treasury implemented changes to URLs for the XML data feeds, the XSD files, and the XML files after the close of business on February 4, 2022. We will continue to update the Developer Notice with any new information, including any date changes.

 

### Temporary Parallel Updates Until February 18, 2022

We continued to publish to the old XML URLs as well as the new XML URLs until February 18 to enable customers to make necessary adjustments.

 

### Data.treasury.gov XML feeds were retired February 18, 2022

After February 18, 2022, we ceased updating the old XML URLs.  The old XML URLs were redirected to the interest rate home page on April 26, 2022.

 

### New URLS for XML feedS as of February 4, 2022

The URLs replacing the data.treasury.gov feeds are:

**Daily Treasury Par Yield Curve Rates**

[https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value=all](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value=all)

**Daily Treasury Bill Rates**

[https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_bill_rates&field_tdr_date_value=all](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_bill_rates&field_tdr_date_value=all)

**Daily Treasury Long-Term Rates**

[https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_long_term_rate&field_tdr_date_value=all](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_long_term_rate&field_tdr_date_value=all)

**Daily Treasury Par Real Yield Curve Rates**

[https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_real_yield_curve&field_tdr_date_value=all](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_real_yield_curve&field_tdr_date_value=all)

**Daily Treasury Real Long-Term Rates**

[https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_real_long_term&field_tdr_date_value=all](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_real_long_term&field_tdr_date_value=all)

 

### New URLs for the Daily XML files as of February 4, 2022

**Daily Treasury Par Yield Curve Rates**

[​https://home.treasury.gov/sites/default/files/interest-rates/yield.xml](https://home.treasury.gov/sites/default/files/interest-rates/yield.xml)

**Daily Treasury Bill Rates**

[https://home.treasury.gov/sites/default/files/interest-rates/daily_treas_bill_rates.xml](https://home.treasury.gov/sites/default/files/interest-rates/real_yield.xml)

**Daily Treasury Long-Term Rates**

[https://home.treasury.gov/sites/default/files/interest-rates/ltcompositeindex.xml](https://home.treasury.gov/sites/default/files/interest-rates/real_yield.xml)

**Daily Treasury Par Real Yield Curve Rates**

[https://home.treasury.gov/sites/default/files/interest-rates/real_yield.xml](https://home.treasury.gov/sites/default/files/interest-rates/real_yield.xml)

**Daily Treasury Real Long-Term Rates**

[https://home.treasury.gov/sites/default/files/interest-rates/real_ltcompositeindex.xml](https://home.treasury.gov/sites/default/files/interest-rates/real_ltcompositeindex.xml)

 

### Redirects

As part of the February 4 activities we implemented redirects on the[table pages](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics)for each of the 5 interest rate data sets. On February 18, we will no longer update the old XML feeds and daily XML files.  At a later date, we will redirect the old XML feeds and files.

 

Here are some additional items we want you to be aware about the February 4, 2022 changes.

### value m:null

Data.treasury.gov XML shows an empty tag to represent an empty value with an attribute m:null = true, whereas the new structure does not have a tag when a corresponding value is not available. Please make sure your application/code checks if element is defined and value is set. If the tag is not shown, that means no data available for that time period.Example of an empty element (data.treasury.gov): <d:BOND_MKT_UNAVAIL_REASON m:null="true" />In the new structure we are not displaying the XML element when the value is null.

 

### Long-Term Rate IDs

In the current data.treasury.gov XML, the self-reference links for the Long-Term rate links to each rate type (BC_20year, Over_10_Years, Real_Rate) ID. The new data structure uses the same three rate type IDs. However, the self-reference link URLs will return null values for the individual rate data.

 

### Real Long-Term IDs

The self-referencing URLs in the ID tag at data.treasury.gov have a date time stamp (QUOTE DATE=datetime'2021-01-05T00%3A00%3A00',RATE=-0.47D). These self-referencing URLs in the Real Long-Term ID XML do not work on data.treasury.gov. This date time stamp will be changed to use an ID in the new structure to reference data for each date.

 

If you have comments or concerns, please notify us at the Feedback link in the footer at the bottom of this page.

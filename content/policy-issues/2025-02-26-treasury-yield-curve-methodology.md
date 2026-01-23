---
date: 2025-02-26
title: Treasury Yield Curve Methodology
url: /policy-issues/treasury-borrowing/interest-rate-statistics/treasury-yield-curve-methodology
draft: false
---

### Treasury Yield Curve Methodology

2/18/2025

***This description was revised and updated on February 18, 2025.***

The Treasury's official yield curve is a par yield curve derived using a monotone convex method. Our inputs are indicative, bid-side market price quotations (not actual transactions) for the most recently auctioned securities obtained by the Federal Reserve Bank of New York at or near 3:30 PM each trading day. The input prices are converted to yields and used to bootstrap the instantaneous forward rates at the input maturity points so that these instruments are sequentially priced without error.  The initial step is followed by a monotone convex interpolation performed on forward rates midway between the input points to construct the entire interest rate curve. This fitting minimizes the price error on the initial price input points, resulting in true par rates.

Treasury reserves the option to make changes to the yield curve as appropriate and in its sole discretion.  Such changes may include but are not necessarily limited to adding, removing, or modifying inputs, and making changes to the methodology for deriving the yield curve.  For example, prior to the re-introduction of the 20-year Treasury bond on May 20, 2020, when the yield curve was derived using a quasi-cubic hermite spline method, the yield curve had used additional inputs that were composites of off-the-run bonds in the 20-year range that reflected market yields available in that maturity range.  Also, at various times in the past, Treasury has used other inputs, such as interpolated yields and rolled down securities deemed necessary for deriving a good fit for the quasi-cubic hermite spline method.

The current inputs are indicative bid-side market price quotations for the most recently auctioned 4-, 6-, 8-, 13-, 17-, 26-, and 52-week bills; the most recently auctioned 2-, 3-, 5-, 7-, and 10-year notes; and the most recently auctioned 20- and 30-year bonds. The inputs for the bills are bid discount rates corresponding to their bond equivalent yields.

Treasury does not provide the computer formulation of our yield curve derivation program. However, most researchers should be able to reasonably match our results using alternative bootstrapping and monotone convex methods.

Treasury reviews its yield curve derivation methodology on a regular basis and reserves the right to modify, adjust or improve the methodology. If Treasury determines that the methodology needs to be changed or updated, Treasury will revise the above description to reflect such changes.

The monotone convex method for deriving the official Treasury yield curve replaced the previous quasi-cubic hermite spline method as of December 6, 2021.  The[description of the previous methodology](https://home.treasury.gov/no-longer-used-yield-curve-methodology)has been archived.

More details regarding the change in yield curve methodology and a comparison of historical CMT rates derived using the monotone convex and the quasi-cubic hermite spline methods are available in the[Yield Curve Methodology Change Information sheet](https://home.treasury.gov/policy-issues/financing-the-government/yield-curve-methodology-change-information-sheet).

[Yield curve rates](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve&field_tdr_date_value=2022)are usually available at[Treasury's interest rate website](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics)by 6:00 PM Eastern Time each trading day, but may be delayed due to system problems or other issues. Every attempt is made to make this data available as soon as possible.

 

**Office of Debt Management****Department of the Treasury**

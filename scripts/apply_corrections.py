#!/usr/bin/env python3
"""
Apply URL corrections to navigation.json and footer.html
"""

import json
import re
from pathlib import Path

# URL corrections mapping
CORRECTIONS = {
    "/about-treasury": "/about",
    "/policy-issues": "/policy-issues/tax-policy",
    "/data": "/data/treasury-coupon-issues-and-corporate-bond-yield-curves",
    "/services": "/services/report-fraud-waste-and-abuse",
    "/policy-issues/coronavirus/american-families-and-workers": "/policy-issues/coronavirus/assistance-for-American-families-and-workers",
    "/policy-issues/coronavirus/small-businesses": "/policy-issues/coronavirus/assistance-for-small-businesses",
    "/policy-issues/coronavirus/state-local-and-tribal-governments": "/policy-issues/coronavirus/assistance-for-state-local-and-tribal-governments",
    "/policy-issues/coronavirus/american-industry": "/policy-issues/coronavirus/assistance-for-american-industry",
    "/policy-issues/tax-policy/treaties-and-related-documents": "/policy-issues/tax-policy/treaties",
    "/policy-issues/tax-policy/reports": "/policy-issues/tax-policy",
    "/policy-issues/tax-policy/tax-analysis": "/policy-issues/tax-policy",
    "/policy-issues/economic-policy/treasury-coupon-issues": "/data/treasury-coupon-issues-and-corporate-bond-yield-curves",
    "/policy-issues/economic-policy/corporate-bond-yield-curve": "/data/treasury-coupon-issues-and-corporate-bond-yield-curve/corporate-bond-yield-curve",
    "/policy-issues/economic-policy/social-security-and-medicare": "/policy-issues/economic-policy",
    "/policy-issues/terrorism-and-illicit-finance/sanctions": "https://ofac.treasury.gov/",
    "/policy-issues/terrorism-and-illicit-finance/asset-forfeiture": "/policy-issues/terrorism-and-illicit-finance/treasury-executive-office-for-asset-forfeiture-teoaf",
    "/policy-issues/terrorism-and-illicit-finance/terrorist-finance-tracking-program": "/policy-issues/terrorism-and-illicit-finance/terrorist-finance-tracking-program-tftp",
    "/policy-issues/financing-the-government/treasury-securities": "https://www.treasurydirect.gov/",
    "/policy-issues/financing-the-government/quarterly-refunding/most-recent-documents": "/policy-issues/financing-the-government/quarterly-refunding/most-recent-quarterly-refunding-documents",
    "/policy-issues/financing-the-government/quarterly-refunding/archives": "/policy-issues/financing-the-government/quarterly-refunding/quarterly-refunding-archives",
    "/policy-issues/financing-the-government/quarterly-refunding/webcasts": "/news/webcasts",
    "/policy-issues/financial-markets-financial-institutions-and-fiscal-service/1603-program": "/policy-issues/financial-markets-financial-institutions-and-fiscal-service/1603-program-payments-for-specified-energy-property-in-lieu-of-tax-credits",
    "/policy-issues/financial-markets-financial-institutions-and-fiscal-service/making-home-affordable": "/data/troubled-assets-relief-program/housing",
    "/policy-issues/international/cfius": "/policy-issues/international/the-committee-on-foreign-investment-in-the-united-states-cfius",
    "/policy-issues/international/us-china-comprehensive-strategic-economic-dialogue": "/policy-issues/international",
    "/policy-issues/small-business-programs/state-small-business-credit-initiative": "https://home.treasury.gov/policy-issues/small-business-programs/state-small-business-credit-initiative-ssbci",
    "/data/treasury-international-capital-tic-system-home-page": "/data/treasury-international-capital-tic-system",
    "/about/offices/tribal-and-native-affairs": "/about/offices/domestic-finance/community-development-financial-institutions/native-initiatives",
    "/about/offices/inspectors-general": "/services/report-fraud-waste-and-abuse/inspectors-general",
    "/about/offices/management/office-of-the-chief-data-officer/evidence-act": "/about/offices/management/office-of-the-chief-data-officer",
    "/about/offices/management/treasury-franchise-fund": "https://www.fiscal.treasury.gov/tff/",
    "/about/offices/management/shared-services-program": "https://www.fiscal.treasury.gov/",
    "/about/history/treasury-library": "/about/history",
    "/about/small-business-contacts": "/policy-issues/small-business-programs/small-and-disadvantaged-business-utilization-0",
    "/services/report-fraud-waste-and-abuse/report-covid-19-scam-attempts": "/services/report-fraud-waste-and-abuse/report-scam-attempts",
    "/services/report-fraud-waste-and-abuse/report-fraud-related-to-government-contracts": "/services/report-fraud-waste-and-abuse/inspectors-general",
    "/services/bonds-and-securities/frequently-asked-questions": "https://www.treasurydirect.gov/help-center/",
    "/services/bonds-and-securities/cashing-savings-bonds-in-disaster-declared-areas": "https://www.treasurydirect.gov/",
    "/services/treasury-payments/lost-or-expired-check": "https://fiscal.treasury.gov/faq/#checks",
    "/services/treasury-payments/non-benefit-federal-payments": "https://fiscal.treasury.gov/",
    "/services/grant-programs/pay-for-results": "/policy-issues/financial-markets-financial-institutions-and-fiscal-service",
    "/services/kline-miller/applications": "/services/the-multiemployer-pension-reform-act-of-2014/applications-for-benefit-suspension",
    "/services/kline-miller/frequently-asked-questions": "/services/the-multiemployer-pension-reform-act-of-2014/frequently-asked-questions-about-the-kline-miller-multiemployer-pension-reform-act",
    "/services/auctions": "https://home.treasury.gov/services/treasury-auctions",
    "/news/press-contacts": "/news/contacts-for-members-of-the-media",
    "/news/weekly-public-schedule-archive": "https://search.usa.gov/search/docs?utf8=%E2%9C%93&affiliate=treas&sort_by=&dc=9123&query=weekly-schedule-updates",
    "/news/media-advisories-archive": "https://search.usa.gov/search/docs?utf8=%E2%9C%93&affiliate=treas&sort_by=&dc=9121&query=media-advisories",
    "/resource-center/data-chart-center/interest-rates/": "/policy-issues/financing-the-government/interest-rate-statistics",
    "https://ofac.treasury.gov/specially-designated-nationals-list-sdn-list/additional-ofac-sanctions-lists": "https://ofac.treasury.gov/specially-designated-nationals-and-blocked-persons-list-sdn-human-readable-lists",
    "https://www.fiscal.treasury.gov/arc/": "https://www.fiscal.treasury.gov/arc.html",
    "https://www.fiscal.treasury.gov/fm/": "https://www.fiscal.treasury.gov/fm.html",
    "https://www.treasurydirect.gov/govt/": "https://www.treasurydirect.gov/",
    "https://www.irs.gov/businesses/small-businesses-self-employed/irs-auctions": "https://www.irsauctions.gov/",
    "https://home.treasury.gov/footer/whistleblower-protection": "https://home.treasury.gov/services/report-fraud-waste-and-abuse",
    "https://home.treasury.gov/about/small-business-contacts": "https://home.treasury.gov/policy-issues/small-business-programs/small-and-disadvantaged-business-utilization-0",
}


def fix_navigation_json():
    """Apply corrections to navigation.json"""
    script_dir = Path(__file__).parent
    nav_file = script_dir.parent / "data" / "navigation.json"
    
    with open(nav_file, 'r') as f:
        content = f.read()
    
    original_content = content
    changes = []
    
    # Apply each correction
    for old_url, new_url in CORRECTIONS.items():
        # Match the URL in JSON format (with quotes)
        old_pattern = f'"{old_url}"'
        new_pattern = f'"{new_url}"'
        
        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
            changes.append(f"  {old_url} → {new_url}")
    
    if changes:
        with open(nav_file, 'w') as f:
            f.write(content)
        print(f"Updated navigation.json with {len(changes)} corrections:")
        for change in changes:
            print(change)
    else:
        print("No changes needed in navigation.json")
    
    return len(changes)


def fix_footer_html():
    """Apply corrections to footer.html"""
    script_dir = Path(__file__).parent
    footer_file = script_dir.parent / "themes" / "treasury" / "layouts" / "partials" / "footer.html"
    
    with open(footer_file, 'r') as f:
        content = f.read()
    
    original_content = content
    changes = []
    
    # Footer-specific corrections
    footer_corrections = {
        "https://www.moneyfactory.gov/": "https://www.bep.gov/",
        "https://www.treasury.gov/tigta/": "https://www.tigta.gov/",
        "https://arc.fiscal.treasury.gov/": "https://www.fiscal.treasury.gov/arc.html",
        "https://www.fiscal.treasury.gov/fm/": "https://www.fiscal.treasury.gov/fm.html",
        "https://www.treasurydirect.gov/govt/": "https://www.treasurydirect.gov/",
        "https://home.treasury.gov/footer/whistleblower-protection": "https://home.treasury.gov/services/report-fraud-waste-and-abuse",
        "https://home.treasury.gov/about/small-business-contacts": "https://home.treasury.gov/policy-issues/small-business-programs/small-and-disadvantaged-business-utilization-0",
    }
    
    for old_url, new_url in footer_corrections.items():
        if old_url in content:
            content = content.replace(old_url, new_url)
            changes.append(f"  {old_url} → {new_url}")
    
    if changes:
        with open(footer_file, 'w') as f:
            f.write(content)
        print(f"\nUpdated footer.html with {len(changes)} corrections:")
        for change in changes:
            print(change)
    else:
        print("\nNo changes needed in footer.html")
    
    return len(changes)


def main():
    print("=" * 80)
    print("Applying URL corrections")
    print("=" * 80)
    print()
    
    nav_changes = fix_navigation_json()
    footer_changes = fix_footer_html()
    
    print()
    print("=" * 80)
    print(f"Total corrections applied: {nav_changes + footer_changes}")
    print("=" * 80)


if __name__ == "__main__":
    main()

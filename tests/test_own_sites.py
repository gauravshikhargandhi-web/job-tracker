"""Readers for companies' own careers sites, each answered with a small sample shaped like the real site."""

import datetime
import json
import unittest
from unittest import mock

from tracker import text
from tracker.boards import (apple, avature, eightfold, eightfold_v2, google, jibe, oracle, successfactors,
                            teamtailor)

TODAY = datetime.date(2026, 10, 15)
SINCE = "2026-10-14"
OCT_15 = 1792065600  # 2026-10-15 12:00 UTC, in seconds
OCT_01 = 1790856000  # 2026-10-01 12:00 UTC

EIGHTFOLD = {"data": {"count": 2, "positions": [
    {"id": 101, "name": "Technical Program Manager", "locations": ["Redmond, Washington, United States"],
     "standardizedLocations": ["Redmond, WA, US"], "postedTs": OCT_15, "department": "Devices"},
    {"id": 102, "name": "Product Manager", "locations": ["Dublin, Ireland"],
     "standardizedLocations": ["Dublin, IE"], "postedTs": OCT_01},
]}}
EIGHTFOLD_V2 = {"count": 1, "positions": [
    {"id": 201, "name": "Consultant", "locations": ["Chicago"], "t_create": OCT_15,
     "canonicalPositionUrl": "https://experiencedtalent.bcg.com/careers/job/201", "job_description": "<p>Advise clients.</p>"}]}
JIBE = {"totalCount": 1, "jobs": [{"data": {
    "slug": "34398", "req_id": "34398", "title": "Program Manager, Launch", "full_location": "Normal, Illinois",
    "country": "United States", "category": ["Manufacturing"], "posted_date": "2026-10-14T18:42:00+0000",
    "description": "<p>Run vehicle launches.</p>"}}]}
ORACLE = {"items": [{"TotalJobsCount": 1, "requisitionList": [
    {"Id": "301", "Title": "Product Manager", "PrimaryLocation": "Chicago, IL, United States",
     "PrimaryLocationCountry": "US", "PostedDate": "2026-10-14"}]}]}
ORACLE_JOB = {"items": [{"ExternalDescriptionStr": "<p>Own the grid products.</p>",
                         "ExternalQualificationsStr": "<p>MBA preferred.</p>"}]}
APPLE = {"res": {"searchResults": [
    {"id": "PIPE-401", "positionId": "401", "postingTitle": "Hardware Program Manager", "postDateInGMT": "2026-10-15T00:00:00Z",
     "locations": [{"name": "Cupertino"}], "transformedPostingTitle": "hardware-program-manager"}]}}
APPLE_JOB = {"res": {"jobSummary": "Lead new product programs.", "minimumQualifications": "5 years"}}
GOOGLE_JOB = ["501", "Program Manager, Devices", None, [None, "<p>Lead launches.</p>"], None, None, None, None, None,
              [["Mountain View, CA, USA", None, None, None, None, "US"]], [None, "<p>Minimum qualifications.</p>"],
              None, [OCT_15]]
GOOGLE_PAGE = ("<html><script>AF_initDataCallback({key: 'ds:1', hash: '2', data:" + json.dumps([[GOOGLE_JOB]])
               + ", sideChannel: {}});</script></html>")
TEAMTAILOR = """<rss><channel><item><title>Operations Manager</title><link>https://career.mutares.com/jobs/601</link>
<guid>601</guid><pubDate>Wed, 14 Oct 2026 09:00:00 +0200</pubDate><description><![CDATA[<p>Turn around companies.</p>]]></description>
<tt:locations><tt:location><tt:city>Chicago</tt:city><tt:country>United States</tt:country></tt:location></tt:locations>
</item></channel></rss>"""
AVATURE = """<rss><channel>
<item><title>Strategy Consultant</title><link>https://apply.deloitte.com/careers/JobDetail/Strategy/701</link>
<pubDate>Wed, 14 Oct 2026 10:00:00 GMT</pubDate></item>
<item><title>Analyst</title><link>https://apply.deloitte.com/careers/JobDetail/Analyst/702</link>
<pubDate>Thu, 01 Oct 2026 10:00:00 GMT</pubDate></item>
</channel></rss>"""
AVATURE_JOB = ('<script type="application/ld+json">' + json.dumps({
    "@type": "JobPosting", "description": "<p>Shape client strategy.</p>",
    "jobLocation": [{"address": {"addressLocality": "Chicago", "addressRegion": "IL", "addressCountry": "US"}}]})
    + "</script>")
SUCCESSFACTORS = """<table><tr class="data-row"><td><a href="/job/St-Louis-Project-Manager-MO/801/" class="jobTitle-link">Project Manager</a>
<span class="jobLocation"> St. Louis, MO, US, 63102 </span><span class="jobDate"> Oct 15, 2026 </span></td></tr></table>"""
SUCCESSFACTORS_JOB = '<div><span class="jobdescription"><p>Lead plant projects.</p></span>\n</div>'


def fake_fetch(url, data=None, headers=None, timeout=60):
    if "/api/pcsx/search" in url:
        answer = EIGHTFOLD if "start=0" in url else {"data": {"count": 2, "positions": []}}
    elif "position_details" in url:
        answer = {"data": {"jobDescription": "<p>Ship Surface devices.</p>"}}
    elif "/api/apply/v2/jobs" in url:
        answer = EIGHTFOLD_V2
    elif "rivian.com/api/jobs" in url:
        answer = JIBE
    elif "recruitingCEJobRequisitions?" in url:
        answer = ORACLE
    elif "recruitingCEJobRequisitionDetails" in url:
        answer = ORACLE_JOB
    elif "jobs.apple.com/api/v1/search" in url:
        answer = APPLE if json.loads(data)["page"] == 1 else {"res": {"searchResults": []}}
    elif "jobDetails" in url:
        answer = APPLE_JOB
    elif "google.com/about/careers" in url:
        return (GOOGLE_PAGE if "page=1&" in url or url.endswith("page=1") else "<html></html>").encode()
    elif "jobs.rss" in url:
        return TEAMTAILOR.encode()
    elif "SearchJobs/feed" in url:
        return AVATURE.encode()  # the same two jobs on every page: paging stops when nothing fresh comes back
    elif "JobDetail" in url:
        return AVATURE_JOB.encode()
    elif "nestle.com/search" in url:
        return (SUCCESSFACTORS if "startrow=0" in url else "<table></table>").encode()
    elif "nestle.com/job/" in url:
        return SUCCESSFACTORS_JOB.encode()
    else:
        raise AssertionError(url)
    return json.dumps(answer).encode()


class OwnSiteTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(text, "fetch", fake_fetch)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_eightfold(self):
        rows = eightfold.collect("Microsoft", {"host": "apply.careers.microsoft.com", "domain": "microsoft.com"},
                                 TODAY, SINCE)
        self.assertEqual([(r["posted"], r["country"]) for r in rows], [("2026-10-15", "US"), ("2026-10-01", "outside the US")])
        self.assertEqual(eightfold.describe(rows[0]), "Ship Surface devices.")

    def test_eightfold_v2(self):
        (row,) = eightfold_v2.collect("BCG", {"host": "experiencedtalent.bcg.com", "domain": "bcg.com"}, TODAY, SINCE)
        self.assertEqual((row["posted"], row["description"]), ("2026-10-15", "Advise clients."))

    def test_jibe(self):
        (row,) = jibe.collect("Rivian", {"host": "careers.rivian.com"}, TODAY, SINCE)
        self.assertEqual((row["posted"], row["country"]), ("2026-10-14", "United States"))
        self.assertEqual(row["link"], "https://careers.rivian.com/careers-home/jobs/34398")

    def test_oracle(self):
        (row,) = oracle.collect("S&C Electric", {"host": "ejia.fa.us6.oraclecloud.com", "site": "CX_1001"}, TODAY, SINCE)
        self.assertEqual((row["posted"], row["country"]), ("2026-10-14", "US"))
        self.assertEqual(oracle.describe(row), "Own the grid products.\nMBA preferred.")

    def test_apple(self):
        (row,) = apple.collect("Apple", {}, TODAY, SINCE)
        self.assertEqual((row["posted"], row["location"]), ("2026-10-15", "Cupertino"))
        self.assertIn("Lead new product programs.", apple.describe(row))

    def test_google(self):
        (row,) = google.collect("Google", {}, TODAY, SINCE)
        self.assertEqual((row["posted"], row["country"]), ("2026-10-15", "US"))
        self.assertIn("Lead launches.", row["description"])

    def test_teamtailor(self):
        (row,) = teamtailor.collect("Mutares", {"host": "career.mutares.com"}, TODAY, SINCE)
        self.assertEqual((row["posted"], row["location"]), ("2026-10-14", "Chicago, United States"))
        self.assertEqual(row["description"], "Turn around companies.")

    def test_avature_stops_paging_when_nothing_new_comes_back(self):
        rows = avature.collect("Deloitte", {"feed": "https://apply.deloitte.com/en_US/careers/SearchJobs/feed/"},
                               TODAY, SINCE)
        self.assertEqual([r["posted"] for r in rows], ["2026-10-14", "2026-10-01"])
        self.assertEqual(avature.describe(rows[0]), "Shape client strategy.")
        self.assertEqual((rows[0]["location"], rows[0]["country"]), ("Chicago, IL", "US"))

    def test_successfactors(self):
        (row,) = successfactors.collect("Nestlé", {"host": "jobdetails.nestle.com"}, TODAY, SINCE)
        self.assertEqual((row["posted"], row["country"]), ("2026-10-15", "US"))
        self.assertEqual(successfactors.describe(row), "Lead plant projects.")


if __name__ == "__main__":
    unittest.main()

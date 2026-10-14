import datetime
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from tracker import boards, run, text, us
from tracker.boards import amazon, ashby, greenhouse, lever, smartrecruiters, workable, workday

HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(HERE)


def sample(name):
    with open(os.path.join(HERE, name), "rb") as f:
        return f.read()


def fake_fetch(url, data=None, headers=None, timeout=60):
    """Answer each board's address with the saved sample."""
    if "greenhouse.io" in url:
        return sample("sample_greenhouse_job.json" if url.rstrip("/").endswith("/7001") else "sample_greenhouse.json")
    if "lever.co" in url:
        return sample("sample_lever.json")
    if "ashbyhq.com" in url:
        return sample("sample_ashby.json")
    if "myworkdayjobs.com" in url:
        if url.endswith("/jobs"):
            return sample("sample_workday.json")
        if url.endswith("_JR3"):
            return json.dumps({"jobPostingInfo": {"startDate": "2026-10-13", "location": "Munich",
                                                  "country": {"descriptor": "Germany"}, "jobDescription": "x"}}).encode()
        return sample("sample_workday_job.json")
    if "smartrecruiters.com" in url:
        if "/postings/" in url:
            return json.dumps({"jobAd": {"sections": {"jobDescription": {"text": "<p>Own connected devices.</p>"}}}}).encode()
        return sample("sample_smartrecruiters.json")
    if "workable.com" in url:
        return sample("sample_workable.json")
    if "amazon.jobs" in url:
        return sample("sample_amazon.json")
    raise AssertionError(url)



TODAY = datetime.date(2026, 10, 14)


class BoardTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(text, "fetch", fake_fetch)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_greenhouse(self):
        rows = greenhouse.collect("Stripe", {"slug": "stripe"}, TODAY)
        self.assertEqual(len(rows), 6)
        tpm = rows[0]
        self.assertEqual(tpm["key"], "Stripe:gh7001")
        self.assertEqual(tpm["posted"], "2026-10-10")
        self.assertEqual(rows[1]["posted"], "")  # updated_at is not the posting date
        self.assertEqual(tpm["description"], "Lead NPI programs for Terminal hardware.\n5+ years in hardware program management")

    def test_lever(self):
        (row,) = lever.collect("Zoox", {"slug": "zoox"}, TODAY)
        self.assertEqual(row["location"], "Foster City, CA; Seattle, WA")
        self.assertIn("3+ years of operations", row["description"])
        self.assertEqual(row["posted"], "2025-10-09")

    def test_ashby_skips_unlisted(self):
        (row,) = ashby.collect("Standard Bots", {"slug": "standardbots"}, TODAY)
        self.assertEqual(row["location"], "New York, NY; Remote - US")
        self.assertEqual(row["posted"], "2026-10-13")

    def test_workday_reads_every_job_and_the_page_gives_the_date(self):
        cfg = {"url": "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"}
        rows = workday.collect("NVIDIA", cfg, TODAY)
        self.assertEqual([r["posted"] for r in rows], ["2026-10-14", "", "2026-10-13"])
        row = rows[0]
        self.assertEqual(row["link"], "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/job/US-CA-Santa-Clara/Senior-TPM_JR2001234")
        self.assertIn("security clearance", boards.describe(row))
        self.assertEqual(row["location"], "US, CA, Santa Clara; Seattle, WA")
        self.assertEqual(row["country"], "United States of America")

    def test_workday_posted_text(self):
        self.assertEqual(workday.posted_on("Posted Today", TODAY), "2026-10-14")
        self.assertEqual(workday.posted_on("Posted Yesterday", TODAY), "2026-10-13")
        self.assertEqual(workday.posted_on("Posted 3 Days Ago", TODAY), "2026-10-11")
        self.assertEqual(workday.posted_on("Posted 30+ Days Ago", TODAY), "")

    def test_smartrecruiters(self):
        (row,) = smartrecruiters.collect("Bosch", {"slug": "BoschGroup"}, TODAY)
        self.assertEqual(row["location"], "Broadview, IL, US")
        self.assertEqual(boards.describe(row), "Own connected devices.")

    def test_workable(self):
        (row,) = workable.collect("CADDi", {"slug": "caddi"}, TODAY)
        self.assertEqual(row["country"], "United States")
        self.assertEqual(row["posted"], "2026-10-12")
        self.assertIn("Master of Business Administration", row["description"])

    def test_amazon(self):
        (row,) = amazon.collect("Amazon", {}, TODAY, "2026-10-13")
        self.assertEqual(row["posted"], "2026-10-10")
        self.assertIn("Preferred qualifications: MBA", row["description"])


class UsTests(unittest.TestCase):
    def test_places(self):
        self.assertTrue(us.is_us("Chicago, IL"))
        self.assertTrue(us.is_us("London; New York, NY"))
        self.assertTrue(us.is_us("Indianapolis, Indiana"))  # India is not Indiana
        self.assertTrue(us.is_us("Remote"))
        self.assertFalse(us.is_us("Dublin, Ireland"))
        self.assertFalse(us.is_us("Remote - Canada"))
        self.assertTrue(us.is_us("Anywhere", "United States; Canada"))
        self.assertFalse(us.is_us("Chicago", "Germany"))


class RunTests(unittest.TestCase):
    """Whole daily runs in a scratch folder, with every board answered from the samples."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        with open(os.path.join(self.dir, "companies.toml"), "w") as f:
            f.write('[[company]]\nname = "Stripe"\nboard = "greenhouse"\nslug = "stripe"\n\n'
                    '[[company]]\nname = "NVIDIA"\nboard = "workday"\nurl = "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"\n\n'
                    '[[company]]\nname = "Apple"\nboard = "not_yet"\nsite = "https://jobs.apple.com"\n\n'
                    '[[company]]\nname = "Broken"\nboard = "greenhouse"\nslug = "broken"\n')
        cwd = os.getcwd()
        os.chdir(self.dir)
        self.addCleanup(os.chdir, cwd)

    def run_day(self, day, fetch):
        with mock.patch.object(text, "fetch", fetch), mock.patch("sys.argv", ["run", "--today", day]):
            run.main()
        return {r["title"]: r for r in run.load(run.DAY_PATH.format(day=day))}

    def fetch(self, url, **kw):
        if "/broken/" in url:
            raise OSError("404")
        return fake_fetch(url, **kw)

    def test_daily_runs(self):
        saved = self.run_day("2026-10-14", self.fetch)
        # NVIDIA: posted today, US. The 30+ days job and the Munich job are left out. Stripe has nothing that recent.
        self.assertEqual(list(saved), ["Senior Technical Program Manager - NPI"])
        self.assertIn("security clearance", saved["Senior Technical Program Manager - NPI"]["description"])
        summary = {r["company"]: r for r in run.load(run.SUMMARY_PATH)}
        self.assertEqual(summary["Stripe"]["open_jobs"], "6")
        self.assertEqual(summary["Broken"]["note"], "Failed today")
        self.assertIn("no reader built yet", summary["Apple"]["note"])

        # Next day: a new Stripe job with no posting date counts as new because it was not there yesterday.
        board = json.loads(sample("sample_greenhouse.json"))
        board["jobs"].append({"id": 7010, "title": "Climate Program Lead", "absolute_url": "https://stripe.com/jobs/7010",
                              "location": {"name": "Seattle, WA"}, "departments": [], "content": "New role."})

        def next_day(url, **kw):
            if "/stripe/jobs" in url:
                return json.dumps(board).encode()
            return self.fetch(url, **kw)

        saved = self.run_day("2026-10-15", next_day)
        self.assertEqual(list(saved), ["Climate Program Lead"])
        self.assertEqual(saved["Climate Program Lead"]["first_seen"], "2026-10-15")


if __name__ == "__main__":
    unittest.main()

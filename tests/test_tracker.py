import datetime
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from tracker import boards, pool, profile, run, text
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
        return sample("sample_workday.json" if url.endswith("/jobs") else "sample_workday_job.json")
    if "smartrecruiters.com" in url:
        if "/postings/" in url:
            return json.dumps({"jobAd": {"sections": {"jobDescription": {"text": "<p>Own connected devices.</p>"}}}}).encode()
        return sample("sample_smartrecruiters.json")
    if "workable.com" in url:
        return sample("sample_workable.json")
    if "amazon.jobs" in url:
        return sample("sample_amazon.json")
    raise AssertionError(url)


PROFILE = profile.load(os.path.join(ROOT, "profile.toml"))


class BoardTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(text, "fetch", fake_fetch)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_greenhouse(self):
        rows = greenhouse.collect("Stripe", {"slug": "stripe"})
        self.assertEqual(len(rows), 6)
        tpm = rows[0]
        self.assertEqual(tpm["key"], "Stripe:gh7001")
        self.assertEqual(tpm["posted"], "2026-10-10")
        self.assertEqual(tpm["department"], "Terminal")
        self.assertEqual(boards.describe(tpm), "Lead NPI programs for Terminal hardware.\n5+ years in hardware program management")
        self.assertEqual(rows[1]["description"], "")

    def test_lever(self):
        (row,) = lever.collect("Zoox", {"slug": "zoox"})
        self.assertEqual(row["location"], "Foster City, CA; Seattle, WA")
        self.assertEqual(row["remote"], "Hybrid")
        self.assertIn("3+ years of operations", row["description"])
        self.assertEqual(row["posted"], "2025-10-09")

    def test_ashby_skips_unlisted(self):
        (row,) = ashby.collect("Standard Bots", {"slug": "standardbots"})
        self.assertEqual(row["location"], "New York, NY; Remote - US")
        self.assertEqual(row["remote"], "Hybrid")

    def test_workday(self):
        cfg = {"url": "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"}
        rows = workday.collect("NVIDIA", cfg, ["MBA", "program manager"])
        self.assertEqual(len(rows), 2)  # the same jobs from two searches are kept once
        row = rows[0]
        self.assertEqual(row["found_by"], "MBA")  # the first word that found it
        self.assertEqual(row["key"], "NVIDIA:wdJR2001234")
        self.assertEqual(row["link"], "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/job/US-CA-Santa-Clara/Senior-TPM_JR2001234")
        self.assertIn("security clearance", boards.describe(row))

    def test_smartrecruiters(self):
        (row,) = smartrecruiters.collect("Bosch", {"slug": "BoschGroup"}, ["product manager"])
        self.assertEqual(row["location"], "Broadview, IL, US")
        self.assertEqual(boards.describe(row), "Own connected devices.")

    def test_workable(self):
        (row,) = workable.collect("CADDi", {"slug": "caddi"})
        self.assertEqual(row["location"], "Chicago, Illinois, United States")
        self.assertEqual(row["posted"], "2026-10-12")
        self.assertIn("Master of Business Administration", row["description"])

    def test_amazon(self):
        (row,) = amazon.collect("Amazon", {}, ["program manager"])
        self.assertEqual(row["posted"], "2026-10-10")
        self.assertEqual(row["link"], "https://www.amazon.jobs/en/jobs/3100001/sr-technical-program-manager")
        self.assertIn("Preferred qualifications: MBA", row["description"])


class ProfileTests(unittest.TestCase):
    def row(self, title, location="Chicago, IL", remote=""):
        return {"title": title, "location": location, "remote": remote}

    def test_titles(self):
        m = lambda t: profile.title_match(PROFILE, t)
        self.assertEqual(m("Sr. Technical Program Manager"), "program: technical program manager")
        self.assertEqual(m("Product Manager, Robotics"), "product: product manager")
        self.assertEqual(m("Technical Project Manager"), "project: technical project manager")
        self.assertEqual(m("New Product Introduction Engineer"), "new_product_and_manufacturing: new product introduction")
        self.assertEqual(m("Manager, Sustainability Strategy"), "sustainability: sustainability")
        self.assertEqual(m("Climate Partnerships Lead"), "sustainability: climate")
        self.assertEqual(m("Project Manager"), "")  # plain project manager is left out
        self.assertEqual(m("Product Marketing Manager"), "")
        self.assertEqual(m("Software Engineer"), "")

    def test_descriptions(self):
        m = lambda t: profile.description_match(PROFILE, t)
        self.assertEqual(m("An MBA preferred, or equivalent."), "business_degree: MBA preferred")
        self.assertEqual(m("Master of Business Administration a plus"), "business_degree: Master of Business Administration")
        self.assertEqual(m("Bachelor's in business administration or finance"), "business_degree: business administration")
        self.assertEqual(m("Bachelor's in engineering"), "")

    def test_drops(self):
        d = lambda *a: profile.drop_title(PROFILE, self.row(*a))
        self.assertEqual(d("Director, Product"), "title: director")
        self.assertEqual(d("Product Manager Intern"), "title: intern")
        self.assertEqual(d("Production Associate, New Product Introduction"), "title: production associate")
        self.assertEqual(d("Maintenance Program Manager"), "title: maintenance")
        self.assertEqual(d("International Program Manager"), "")  # "intern" is a whole word only
        self.assertEqual(d("Salesforce Product Manager"), "")     # so is "sales"
        self.assertEqual(d("Product Manager", "Dublin, Ireland"), "location: Dublin, Ireland")
        self.assertEqual(d("Product Manager", "London; New York, NY"), "")
        self.assertEqual(d("Product Manager", "Indianapolis, Indiana"), "")  # India is not Indiana
        self.assertEqual(profile.drop_description(PROFILE, "Requires an active security clearance."),
                         "description: security clearance")
        self.assertEqual(profile.sponsorship(PROFILE, "We are unable to sponsor visas."), "No sponsorship")
        self.assertEqual(profile.sponsorship(PROFILE, "We sponsor H-1B visas."), "")

    def test_area(self):
        a = lambda *r: profile.area(PROFILE, self.row("x", *r))
        self.assertEqual(a("Chicago, IL"), "Chicago")
        self.assertEqual(a("Foster City, CA; Seattle, WA"), "Seattle, Bay Area")
        self.assertEqual(a("Austin, TX", "Remote"), "Remote")
        self.assertEqual(a("Austin, TX"), "")


class RunTests(unittest.TestCase):
    """A whole daily run in a scratch folder, with every board answered from the samples."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        shutil.copy(os.path.join(ROOT, "profile.toml"), self.dir)
        with open(os.path.join(self.dir, "companies.toml"), "w") as f:
            f.write('[[company]]\nname = "Stripe"\nboard = "greenhouse"\nslug = "stripe"\n\n'
                    '[[company]]\nname = "Zoox"\nboard = "lever"\nslug = "zoox"\n\n'
                    '[[company]]\nname = "NVIDIA"\nboard = "workday"\nurl = "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"\n\n'
                    '[[company]]\nname = "Apple"\nboard = "not_yet"\nsite = "https://jobs.apple.com"\n\n'
                    '[[company]]\nname = "Broken"\nboard = "greenhouse"\nslug = "broken"\n')
        cwd = os.getcwd()
        os.chdir(self.dir)
        self.addCleanup(os.chdir, cwd)

    def fetch(self, url, **kw):
        if "/broken/" in url:
            raise OSError("404")
        return fake_fetch(url, **kw)

    def run_day(self, day, fetch=None):
        with mock.patch.object(text, "fetch", fetch or self.fetch), mock.patch("sys.argv", ["run", "--today", day]):
            run.main()

    def test_daily_run(self):
        self.run_day("2026-10-14")
        matches = {m["title"]: m for m in pool.load(run.MATCHES_PATH)}
        self.assertEqual(sorted(matches), ["Product Operations Manager", "Strategy and Business Operations Associate",
                                           "Technical Program Manager, Hardware NPI"])
        self.assertEqual(matches["Strategy and Business Operations Associate"]["why"], "business_degree: MBA preferred")
        self.assertEqual(matches["Strategy and Business Operations Associate"]["sponsor"], "No sponsorship")
        self.assertEqual(matches["Strategy and Business Operations Associate"]["area"], "Chicago")
        self.assertEqual(matches["Product Operations Manager"]["sponsor"], "No sponsorship")
        self.assertEqual(len(pool.load(run.NEW_PATH)), 3)  # on the first day every match is new
        reasons = {r["title"]: r["filtered_reason"] for r in pool.load(run.FILTERED_PATH)}
        self.assertEqual(reasons["Senior Technical Program Manager - NPI"], "description: security clearance")
        self.assertEqual(reasons["Principal Program Manager"], "title: principal")
        self.assertEqual(reasons["Director, Product Management"], "title: director")
        self.assertEqual(reasons["Enterprise Sales Manager"], "title: sales")
        self.assertEqual(reasons["Product Manager, Billing"], "location: Dublin, Ireland")
        summary = {r["name"]: r for r in pool.load(run.SUMMARY_PATH) if r["section"] == "company"}
        self.assertIn("failed today", summary["Broken"]["note"])
        self.assertIn("no reader built yet", summary["Apple"]["note"])

        # The next day: nothing is new, Workday job pages are not opened again,
        # and a match that closed moves to the archive.
        opened = []
        gone = json.loads(sample("sample_greenhouse.json"))
        gone["jobs"] = gone["jobs"][1:]

        def next_day(url, **kw):
            if "/wday/cxs/" in url and not url.endswith("/jobs"):
                opened.append(url)
            if "/stripe/jobs" in url:
                return json.dumps(gone).encode()
            return self.fetch(url, **kw)

        self.run_day("2026-10-15", next_day)
        self.assertEqual(opened, [])
        self.assertEqual(pool.load(run.NEW_PATH), [])
        self.assertEqual(sorted(m["title"] for m in pool.load(run.MATCHES_PATH)),
                         ["Product Operations Manager", "Strategy and Business Operations Associate"])
        archived = pool.load(run.ARCHIVE_PATH.format(year=2026))
        self.assertEqual([a["title"] for a in archived], ["Technical Program Manager, Hardware NPI"])


if __name__ == "__main__":
    unittest.main()

"""Is a job in the US? Uses the country when the board gives one, else the place names."""

import re

US_COUNTRIES = {"us", "usa", "united states", "united states of america", "u.s.", "u.s.a."}

# Places outside the US. A job is dropped only when every place it lists is one of these.
ABROAD = [
    "Canada", "Toronto", "Vancouver", "Montreal", "Mexico", "Brazil", "Argentina", "Colombia", "Chile",
    "Costa Rica", "United Kingdom", "UK", "London", "Ireland", "Dublin", "Germany", "Berlin", "Munich", "France",
    "Paris", "Netherlands", "Amsterdam", "Spain", "Madrid", "Barcelona", "Italy", "Milan", "Poland", "Warsaw",
    "Switzerland", "Zurich", "Sweden", "Stockholm", "Denmark", "Billund", "Copenhagen", "Belgium", "Austria",
    "Czech", "Hungary", "Portugal", "Lisbon", "Israel", "Tel Aviv", "India", "Bangalore", "Bengaluru", "Hyderabad",
    "Pune", "Mumbai", "Delhi", "Gurgaon", "Gurugram", "Chennai", "China", "Shanghai", "Beijing", "Shenzhen",
    "Hong Kong", "Taiwan", "Taipei", "Japan", "Tokyo", "Korea", "Seoul", "Singapore", "Malaysia", "Philippines",
    "Vietnam", "Thailand", "Indonesia", "Australia", "Sydney", "Melbourne", "New Zealand", "Dubai",
    "United Arab Emirates", "Saudi", "Qatar", "South Africa", "Nigeria", "Kenya", "Egypt", "Turkey", "Istanbul",
    "Finland", "Norway", "Oslo", "Europe", "Asia", "Pacific", "Latin America", "Romania", "Bucharest", "Finland",
    "Helsinki", "Palestine", "Greece", "Ukraine", "Serbia", "Bulgaria", "Estonia", "Lithuania", "Latvia",
    "Slovakia", "Croatia", "Peru", "Uruguay", "Pakistan", "Bangladesh", "Sri Lanka", "Morocco", "Ghana",
    "Luxembourg", "Scotland", "Edinburgh", "Cambridge, UK", "Belfast", "Krakow", "Prague", "Budapest", "Vienna",
    "Hamburg", "Frankfurt", "Rotterdam", "BRA", "FRA", "MEX", "GBR", "DEU", "CAN", "IRL", "ESP", "NLD", "POL",
    "CHN", "SGP", "AUS", "ISR", "JPN", "ITA", "CRI", "ROU", "HUN", "CZE", "KOR", "TWN", "PHL", "ARE", "SAU",
]
_ABROAD = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(w) for w in sorted(ABROAD, key=len, reverse=True)) + r")(?!\w)",
                     re.I)


def is_us(location, country=""):
    """True for US jobs, remote US jobs and jobs whose place is unknown; False when every place is abroad."""
    if country:
        return any(c.strip().lower() in US_COUNTRIES for c in country.split(";"))
    places = [p for p in re.split(r";|\|| / | or ", location or "") if p.strip()]
    return not places or not all(_ABROAD.search(p) for p in places)

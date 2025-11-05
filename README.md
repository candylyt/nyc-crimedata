**COMS 4111: Introduction to Database**

**Yuting Liu(yl5961), Sally Go(yg3066)**

**PostgreSQL Account:** yl5961

**URL of the Web Application:** http://34.148.79.232:8111/

(note: do not turn off the virtual machine so that the external IP address remains the same)

**Proposed & Implemented Features (proposed in part 1):**

For general users



* **Exploration & Search**: Users can browse historical crime records and filter results by categories such as date of occurrence, gender of victim, crime type, law category, and etc, enabling them to explore safety trends in neighborhoods of interest.
* **Personalized Risk Assessment**: By entering personal information (e.g., gender, race, age group), users can receive tailored recommendations on safer neighborhoods. Alternatively, they can provide a postal code and receive an assessment on whether the area is recommended for their demographic profile.

For administrators



* **Reporting**: Admins can submit new reports of incidents, including associated suspects and victims. 
    * Admins should also be able to add new victims & suspects for the existing incidents
* **Incident Management**: Admins can update the status and details of reported incidents, such as changing an incident’s status from Open to Closed, or modifying suspect arrest status.
* **Data Integrity**: Admins can remove incidents flagged as false reports to maintain the reliability of the database.
* **System Expansion**: Admins can create new crime types, and jurisdictions. 
    * (Note: We removed the law categories from the proposal as we believe that this shall not 
    * be changed in real life)

*All features proposed in part 1 are implemented.

**Additional Features (not proposed in part 1)**:

For general users



* **Incident Analysis**: The Incident Analysis module allows users to explore key crime trends and demographic insights from the most recent database.
    * Users can view the **Top 10 Crime Types** (ranked by the number of incidents) across New York City or within a specific borough, based on the selected time window — such as the past 90 days, 1, 3, 5, or 10 years, or the complete dataset dating back to 1981.
    * Users can analyze **crime type distributions** within a particular postal code based on victim demographics — including gender, race, and age group. This enables users to identify which crime types are more prevalent for individuals with similar profiles in their area, offering a personalized understanding of local safety risks.
    * Users can explore the **crime trend over time**, visualizing how the total number of incidents has evolved from 1981 to 2025. Users can specify a custom range of years, select a particular crime type, and filter by borough to focus on trends relevant to their interests or regions of concern.

**Interesting Web Pages**

**Web Page: Incident Analysis**

The Incident Analysis page is designed to help users explore and understand crime trends and demographic patterns in New York City. It allows users to generate data-driven insights by querying the latest database for three main purposes:



1. To view the Top 10 Crime Types, ranked by the number of incidents, across the entire city or within a selected borough and time window.
2. To analyze crime distributions within a specific postal code, filtered by victim’s demographics such as gender, race, and age group, providing a more personalized perspective on local safety conditions.
3. To explore crime trends over time, where users can visualize how the total number of incidents has evolved between 1981 and 2025. Besides the default trend, users can further specify a custom range of years, as well as filter by borough and crime type, to examine long-term patterns or identify shifts in specific categories of crime.

The page interacts with the database through the following operations:



* User inputs, such as borough, time window, postal code, age group, gender, race, year range, and crime types are collected from form fields on the web page. Not all inputs are required to generate results (i.e., users can freely combine any subset of filters based on their inputs). These inputs are then transformed into SQL query parameters and incorporated into dynamically constructed queries. 
* The database executes these queries to:
    * Aggregate incidents counts by crime type and rank the top 10 results. In the case of a tie at the 10th rank, all crime types with the same number of incidents are returned to provide a more complete view of the ranking.
    * Filter incidents by postal code and victim’s demographics to calculate the total number of incidents for each crime type corresponding to a specific population group. 
    * Aggregate the number of reported incidents by year to identify temporal trends, showing how crime levels evolve over time under selected conditions.

What makes this page interesting is the fact that it bridges raw crime data with user-centered, actionable insights. It transforms a large, complex crime dataset into an interactive analytical tool, enabling users to uncover spatial, temporal and demographic crime patterns that are otherwise difficult to observe. The customizable filters (time window, borough, and demographics) make the analysis highly flexible and personalized, supporting various use cases such as public policy planning and personal safety awareness. 

**Web Page: Personalized Recommendations**

The Personalized Recommendations page turns NYC crime records into guidance tailored to each user’s profile. It supports two complementary goals:



1. Find the Top 10 Safest Areas (for your demographic).
 Given a gender, age group, and race, the page ranks postal-code/borough pairs by how *rarely* incidents in that area involve people (i.e., victim) matching that demographic.
2. Assess Risk in Your Neighborhood.
 Given a postal code (plus optional gender, age group, and race), the page estimates how likely incidents in that area involve someone like the user and assigns a simple Low / Moderate / High risk label.

**How it interacts with the database:** Users can provide any subset of: postal code, gender, age group, and race. (All fields are optional for the Top-10; the postal code is used on the right-hand “Assess Risk” panel.)

Queries & Computations:



* Demographic match rate.
For each postal code (joined with its borough), the system counts:
    * Total incidents in that area.
    * Matching incidents where at least one victim’s gender/age/race equals the user’s selections (empty fields are treated as “any”). It then computes a match percentage = matching_incidents / total_incidents. \

* Top 10 Safest Areas.
Areas are sorted by *ascending* match percentage (lower ⇒ safer for the chosen demographic). Ties at the cutoff are included so no equally ranked area is omitted. To avoid bias from tiny sample sizes, the query can optionally require a minimum incident count; when enabled, areas below the threshold are excluded from ranking. \

* Neighborhood Risk (by postal code).
For the entered postal code, the same match percentage is computed. The page also shows the raw counts:
    * total incidents,
    * incidents involving the selected demographic,

    * the resulting percentage (the “likelihood to become a target” for that profile in that area).

* A categorical risk label is then assigned using simple, explainable thresholds (configurable in code). For example:
    * Low: match % ≤ 10%
    * Moderate: 10% &lt; match % ≤ 25%
    * High: match % > 25%

* These thresholds are intentionally transparent and can be tuned as the team sees fit.

This page is especially interesting because it turns city-wide crime records into a person-centric view of safety, reframing raw counts into measures of relative exposure for specific demographics so you can compare neighborhoods in a way that actually matters to you. It stays clear with simple percentages and plain-language risk categories while remaining flexible: you can combine any demographic filters you care about such as gender, age group, and race, and see how often incidents in a ZIP code involve people like you. The result is a practical tool for everyday decisions, from personal awareness and housing choices to community outreach, highlighting places where incidents involving your demographic are less common and expressing local risk in straightforward terms.

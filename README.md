CueBox Client Onboarding – Data Transformation Project
1. Overview

This project simulates a real client onboarding task for CueBox.

The goal is to transform three input data exports from a legacy system into two CSV files for client sign-off and import into CueBox.

The data covers constituents, their emails, and their donation history.

Data quality is critical because the information is used for marketing and fundraising outreach.

2. Inputs

All input files are located in the data/ folder.

constituents.csv
One row per constituent (Patron ID), including names, company, salutation, and tags.

emails.csv
Additional emails per constituent (multiple rows per Patron ID).

donations.csv
Donation transactions (multiple rows per Patron ID).

3. Outputs

All generated files are written to the output/ folder.

3.1 CueBox_Constituents.csv

One row per constituent, formatted for the CueBox Constituents import.

Includes:

Normalized names and company information

Standardized emails

Mapped and cleaned tags

Donation aggregates (lifetime total and most recent donation)

Background information

3.2 CueBox_Tags.csv

A summary file with:

One row per tag

The number of unique constituents associated with each tag

3.3 qa_constituents.csv

A quality-assurance report that:

Lists missing required fields

Lists invalid values

Lists rule violations (e.g. Email 2 without Email 1)

This file helps identify issues before client sign-off or import.

4. Project Structure

cuebox-onboarding/

  requirements.txt
  
  README.md
  
  config.py
  
  helpers.py
  
  make_constituents.py
  
  make_tags.py
  
  data/
  
    constituents.csv
    
    emails.csv
    
    donations.csv
    
  output/
  
    CueBox_Constituents.csv
    
    CueBox_Tags.csv
    
    qa_constituents.csv

6. File Overview

requirements.txt
Python dependencies required to run the project.

config.py
Central configuration (API URLs and cache paths).

helpers.py
Shared utility functions (email parsing, tag mapping, donation aggregation).

make_constituents.py
Generates the CueBox Constituents output (Output #1).

make_tags.py
Generates the CueBox Tags output (Output #2).

6. Setup Instructions

Ensure Python 3.10 or newer is installed.

Verify installation using:

python --version


Install dependencies using:

python -m pip install -r requirements.txt

7. How to Run
7.1 Generate CueBox Constituents (Output #1)
python make_constituents.py --constituents data/constituents.csv --emails data/emails.csv --donations data/donations.csv


This creates:

output/CueBox_Constituents.csv

output/qa_constituents.csv

7.2 Generate CueBox Tags (Output #2)
python make_tags.py --constituents data/constituents.csv


This creates:

output/CueBox_Tags.csv

8. Data Transformations & Business Rules
8.1 Constituent Type

If Company is populated and First Name and Last Name are empty, the type is Company.

Otherwise, the type is Person.

8.2 Emails

Email 1 is the Primary Email if valid, otherwise the first valid email from the Emails input.

Email 2 is the second valid and distinct email.

Email 2 must not exist if Email 1 is missing.

Emails are trimmed, lower-cased, and validated for basic format.

8.3 Salutation & Gender

Salutation is normalized to Mr., Mrs., Ms., Dr., or empty.

Gender is inferred from salutation if needed in the future, but is not included as a separate output field.

8.4 Tags

Tags are split by comma.

Whitespace is trimmed.

Duplicate tags per constituent are removed.

Tags are mapped using a client-provided API (name → mapped_name).

If a tag is not found in the API, the original value is kept.

8.5 Background Information

Includes Job Title only.

Format: Job Title: Marketing Manager.

Empty if job title is missing.

8.6 Donations

Only donations with Status = Paid are considered.

Lifetime Donation Amount is the sum of all donations.

Most Recent Donation Date is the latest donation date.

Most Recent Donation Amount is the amount of that donation.

Amounts are formatted as $1,234.56.

9. Validation & QA

The project performs automatic validation.

Checks include unique constituent IDs, required timestamps, valid titles, email rules, and duplicate records.

Results are written to qa_constituents.csv to ensure data quality before import.

10. Assumptions & Decisions

Gender is derived from Salutation, not from the source “Gender” column.

The source “Gender” column was ignored because its values did not represent gender.

Constituents with both personal name and company were treated as Person records.

If the tag-mapping API is unavailable, tags are kept unchanged.

Donations without a matching constituent are ignored.

All assumptions are documented for transparency and review with the Client Success Manager.

11. AI Tool Usage

AI tools were used to help structure the transformation logic.

AI tools were used to validate business rules.

AI tools were used to improve code readability and documentation.

All final decisions and code were reviewed and adjusted manually.

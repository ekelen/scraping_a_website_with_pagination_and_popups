# Description
Write a Python script to scrape data from the following website https://www.psychologytoday.com/us/therapists in the following manner:<br>
Step 1 –The script will go one state at a time from the UNITED STATES section (Alaska to Wyoming), but it can also combine all states in one scraping step per gender in step 2 below<br>
Step 2 – Once inside a State such as this one https://www.psychologytoday.com/us/therapists/alabama, it will filter by Gender (Women, Men, Non-Binary). Each gender will get its own CSV, so the total output per State are 3 CSVs.<br>
Step 3 - Once inside a State, it will go to each therapist, one by one by clicking the VIEW button (including therapists on all the subsequent pages)<br>
Step 4 – Once it’s on an individual therapist’s page such as this one https://www.psychologytoday.com/us/therapists/dannette-bivins-birmingham-al/443641, it will scrape the following information into the respective CSV in the order shown below 
- State 
- City 
- Street Address 1 
- Street Address 2 
- Zip Code 1
- Zip Code 2
- Business Name 
- Person’s Name 
- Title 
- Telephone 
- Insurance 
- Specialties and Expertise 
- Types of Therapy 
- Age

# Contributors
Leonard Gachimu

# License
This project is licensed under the [MIT License](https://github.com/leogachimu/scraping_a_website_with_pagination_and_popups/blob/main/LICENSE).

Feel free to contribute or raise feedback.

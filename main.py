from os import getenv
from spreadsheet import write_spreadsheet 
from driver import setup_driver
from ticket import login_ticket, set_state, show_all_entries, normalize, wait_loading_finish, get_main_data, get_ticket_data

def main():
    username = getenv("MY_USERNAME")
    password = getenv("MY_PASSWORD")
    if username and password:
        driver = setup_driver(True)
        login_ticket(driver, username, password)
        print("connected.")
        set_state(driver, "DC")
        wait_loading_finish(driver)
        show_all_entries(driver)
        data = get_main_data(driver)
        tickets = get_ticket_data(driver, data)
        driver.quit()
        normalized = normalize(tickets)
        write_spreadsheet("data.xlsx", normalized)
    else:
        print("username/password secrets not set.")

def dummy_data():
    id="26051986"
    release_date= "01/23/26 12:20 pm"	
    response_date = "01/28/26 12:30 pm"
    cross_street= "QUINCY PL NW"	
    expire_date= "02/13/26 12:30 pm"
    url = "https://md.itic.occinc.com/excavatorTicketView?ienc=Sj7o4OkUbIVvLJofFsrb3IRWjRB2Z/mLDXTLUWJj1Xk="
    url2="https://md.itic.occinc.com/excavatorTicketView?ienc=XMah5PSf8nUNd8/0qy7Ln4RWjRB2Z/mLDXTLUWJj1Xk="
    ticket = dict(id_ticket=id,url=url,release_date=release_date,response_date=response_date,cross_street=cross_street,expire_date=expire_date)
    ticket2 = dict(id_ticket="26080558",url=url2,release_date=release_date,response_date=response_date,cross_street=cross_street,expire_date=expire_date)
    return [ticket, ticket2]
    

if __name__ == "__main__":
    main()

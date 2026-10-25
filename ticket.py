from typing import Optional
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from utils import cleared_date, delay, expire_date_days, is_completed_status_history, is_expired_ticket, overdue_date, format_not_completed_status_history, get_not_completed_status_history
from driver import find_element_or_none, find_elements, get_text, click_btn
from typing import Optional, Dict
from re import match


class Ticket:
    def __init__(
        self,
        job_name: Optional[str] = None,
        cross_street: Optional[str] = None,
        ticket_type: Optional[str] = None,
        status: Optional[str] = None,
        id_ticket: Optional[str] = None,
        former_id_ticket: Optional[str] = None,
        release_date: Optional[str] = None,
        response_date: Optional[str] = None,
        expire_date: Optional[str] = None,
        permit: Optional[str] = None,
        days_to_expire: Optional[str] = None,
        cleared_ticket_date: Optional[str] = None,
        days_overdue: Optional[str] = None
    ):
        self.job_name = job_name
        self.cross_street = cross_street
        self.ticket_type = ticket_type
        self.status = status
        self.id_ticket = id_ticket
        self.former_id_ticket = former_id_ticket
        self.release_date = release_date
        self.response_date = response_date
        self.expire_date = expire_date
        self.permit = permit
        self.days_to_expire = days_to_expire
        self.cleared_ticket_date = cleared_ticket_date
        self.days_overdue = days_overdue
    
    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            'job_name': self.job_name,
            'cross_street': self.cross_street,
            'ticket_type': self.ticket_type,
            'status': self.status,
            'id_ticket': self.id_ticket,
            'former_id_ticket': self.former_id_ticket,
            'release_date': self.release_date,
            'response_date': self.response_date,
            'expire_date': self.expire_date,
            'permit': self.permit,
            'days_to_expire': self.days_to_expire,
            'cleared_ticket_date': self.cleared_ticket_date,
            'days_overdue': self.days_overdue
        }


def login_ticket(driver: WebDriver, username: str, password: str) -> None:
    base = "https://md.itic.occinc.com/excavatorTickets"
    username_xpath = '//*[@id="username"]'
    pwd_xpath = '//*[@id="pass"]'
    login_xpath = '//*[@id="btn-login"]'
    driver.get(base)
    wait =  WebDriverWait(driver, 5)

    username_elm = find_element_or_none(wait, username_xpath)
    if username_elm:
        delay(1, 2)
        username_elm.send_keys(username)

    pwd_elm = find_element_or_none(wait, pwd_xpath)
    if pwd_elm:
        delay(1, 2)
        pwd_elm.send_keys(password)

    login_btn = find_element_or_none(wait, login_xpath)
    if login_btn:
        login_btn.click()

def _is_state_match(text: str, state: str) -> bool:
    t = " ".join((text or "").upper().replace(".", "").split())
    names = {"DC": ["DC", "DISTRICT OF COLUMBIA", "WASHINGTON DC"]}
    targets = names.get(state.upper(), [state.upper()])
    return t in targets or any(t.startswith(n + " ") or t.endswith(" " + n) or f"({n})" in t for n in targets)


def set_state(driver: WebDriver, state: str = "DC") -> bool:
    """Open the 'set state' page and choose the given state, then return to the ticket list."""
    from selenium.webdriver.support.ui import Select
    set_state_url = "https://md.itic.occinc.com/excavatorSetState"
    tickets_url = "https://md.itic.occinc.com/excavatorTickets"
    delay(2, 3)
    driver.get(set_state_url)
    delay(3, 5)
    print(f"set state page: {driver.current_url} | title: {driver.title!r}")
    chosen = False

    # 1) Dropdowns
    for sel in driver.find_elements(By.TAG_NAME, "select"):
        try:
            s = Select(sel)
            for opt in s.options:
                val = (opt.get_attribute("value") or "")
                if _is_state_match(opt.text, state) or val.strip().upper() == state.upper():
                    s.select_by_visible_text(opt.text)
                    print(f"selected state option: {opt.text!r} (value={val!r})")
                    chosen = True
                    break
        except Exception as e:
            print(f"could not use dropdown: {e}")
        if chosen:
            break

    # 2) Radio buttons / links / buttons labelled with the state
    if not chosen:
        for elm in driver.find_elements(By.XPATH, "//input[@type='radio'] | //label | //a | //button | //li | //span | //div[not(*)]"):
            try:
                label = elm.text or elm.get_attribute("value") or ""
                if elm.is_displayed() and _is_state_match(label, state):
                    elm.click()
                    print(f"clicked state element: <{elm.tag_name}> {label!r}")
                    chosen = True
                    break
            except Exception:
                continue

    # Submit if the page has a submit/continue button
    if chosen:
        delay(1, 2)
        submit_words = {"continue", "submit", "save", "set state", "set", "go", "ok", "select", "change state", "change"}
        for btn in driver.find_elements(By.XPATH, "//button | //input[@type='submit' or @type='button']"):
            try:
                label = " ".join((btn.text or btn.get_attribute("value") or "").lower().split())
                is_submit = (btn.get_attribute("type") or "").lower() == "submit"
                if btn.is_displayed() and (label in submit_words or (is_submit and "log" not in label)):
                    print(f"clicking submit: {label!r}")
                    btn.click()
                    break
            except Exception:
                continue
        delay(3, 5)
    else:
        # Print what is on the page so the selectors can be adjusted
        print(f"WARNING: could not find state {state!r} on the set-state page. Page elements:")
        for sel in driver.find_elements(By.TAG_NAME, "select"):
            opts = [o.text for o in Select(sel).options][:60]
            print(f"  select id={sel.get_attribute('id')!r} name={sel.get_attribute('name')!r} options={opts}")
        for elm in driver.find_elements(By.XPATH, "//a | //button | //input[@type='submit' or @type='radio' or @type='button']")[:80]:
            try:
                print(f"  <{elm.tag_name}> id={elm.get_attribute('id')!r} text={(elm.text or elm.get_attribute('value') or '').strip()[:60]!r}")
            except Exception:
                pass

    driver.get(tickets_url)
    print(f"back on tickets page: {driver.current_url}")
    return chosen


from time import sleep
def wait_loading_finish(driver: WebDriver):
    print("waiting data to finish loading, sleeping 5 minutes.")
    sleep(5*60)
    wait_loading = WebDriverWait(driver, 5*60)
    loading_locator = (By.XPATH, '//*[@id="loading_block"]')
    try:
        wait_loading.until(EC.invisibility_of_element_located(loading_locator))
    except TimeoutException:
        pass


def get_main_data(driver: WebDriver) -> list[dict]:
    driver.execute_script("document.body.style.zoom='50%'")
    tickets = find_elements(WebDriverWait(driver, 5), '//*[@id="ExcavatorTicketTable"]/tbody/tr')
    data = []
    if tickets:
        print(f"total {len(tickets)} tickets found.")
        fields_xpath = '//th[not(@style="display:none")]'
        fields = get_fields(WebDriverWait(driver, 5), fields_xpath)
        col_release = lookup_field("release", fields)
        col_response = lookup_field("response", fields)
        col_cross_street = lookup_field("cross street", fields)
        col_expiration = lookup_field("expiration", fields)
        col_id = lookup_field("ticket #", fields)
        needed = max(col_release, col_response, col_cross_street, col_expiration, col_id)
        for t in tickets:
            cells = t.find_elements(By.XPATH, './td')
            if len(cells) < needed or 0 in (col_release, col_response, col_cross_street, col_expiration, col_id):
                print(f"skipping row (not a ticket): {t.text.strip()!r}")
                continue
            expire_date = t.find_element(By.XPATH, f'./td[{col_expiration}]').text
            days_to_expire = expire_date_days(expire_date)
            if is_expired_ticket(days_to_expire):
                continue

            id = t.find_element(By.XPATH, f'./td[{col_id}]/a').text
            url = t.find_element(By.XPATH, f'./td[{col_id}]/a').get_attribute('href')
            release_date = t.find_element(By.XPATH, f'./td[{col_release}]').text
            response_date = t.find_element(By.XPATH, f'./td[{col_response}]').text
            cross_street = t.find_element(By.XPATH, f'./td[{col_cross_street}]').text.strip()
            ticket = dict(id_ticket=id,url=url,release_date=release_date,response_date=response_date,cross_street=cross_street,expire_date=expire_date)
            data.append(ticket)
    return data


def get_ticket_data(driver: WebDriver, data: list[dict]) -> list[dict]:
    tickets_data = []
    wait = WebDriverWait(driver, 4)
    print(f"scraping {len(data)} non-expired tickets.")
    for ticket in data:
        print(ticket.get("id_ticket"))
        ticket_data = dict()
        ticket_data.update(ticket)
        driver.get(ticket["url"])
        print(f"{ticket['url']}")
        delay(1, 3)
        click_btn(wait,'/html/body/div[6]/div[3]/div/button')
        job_name_elm = get_text(wait, '//*[@id="tktRem"]')
        if not job_name_elm:
            print("jobname not found")
        print("job: ", job_name_elm)

        elm = get_text(wait, '//*[@id="collapsable1"]/div[2]/div[1]/span')

        if elm:
            is_update_of = elm.lower() == 'update of'
            if is_update_of:
                update_of = get_text(wait, '//*[@id="collapsable1"]/div[2]/div[2]/a/span')
                ticket_data.update(former_id_ticket=update_of)
        #ticket_type = get_text(wait,'//*[@id="collapsable1"]/div[last()]/div[2]')
        #if ticket_type:
        #    ticket_type = ticket_type.replace("\n", " ")
        status_history_elm = find_elements(wait, '//*[@id="DistrictNotificationTable"]/tbody/tr')
        print(status_history_elm)
        if status_history_elm:
            history = []
            for row in status_history_elm:
                sh = dict()
                district = row.find_element(By.XPATH,'./td[1]').text
                status = row.find_element(By.XPATH,'./td[last()]').text
                sh[district] = status
                history.append(sh)
            ticket_data.update(status_history=history)
        ticket_data.update(job_name=job_name_elm)
        tickets_data.append(ticket_data)
        print("FInish")
    return tickets_data


def normalize(tickets: list[dict]) -> list[dict]:
    normalized_t = []
    for t in tickets:
        ticket = Ticket()
        ticket.job_name = t.get("job_name")
        ticket.cross_street = t.get("cross_street")
        ticket.ticket_type = "New"
        ticket.id_ticket = t.get("id_ticket")
        ticket.former_id_ticket = t.get("former_id_ticket")
        if ticket.former_id_ticket:
            ticket.ticket_type = "Update-Renewal"
        ticket.release_date = t.get("release_date")
        ticket.response_date = t.get("response_date")
        ticket.expire_date = t.get("expire_date")
        ticket.days_overdue = t.get("days_overdue")
        expire = t.get("expire_date")
        history = t.get("status_history")
        ticket.cleared_ticket_date = None
        if expire and history:
            days_to_expire = expire_date_days(expire)
            ticket.days_to_expire = str(days_to_expire)
            ####
            status = is_completed_status_history(history)
            #if status:
            #    continue
            ####
            not_complete = get_not_completed_status_history(history)
            formatted_status = format_not_completed_status_history(not_complete)
            ticket.permit = formatted_status
            status = "closed" if status else "pending"
            if status == "pending":
                days_overdue = overdue_date(expire)
                ticket.days_overdue = days_overdue
            if status == "closed":
                cleared_ticket_date = cleared_date()
                ticket.cleared_ticket_date = cleared_ticket_date
            ticket.status = status
        normalized_t.append(ticket.to_dict())

    return normalized_t


def lookup_field(s: str, fields: list[list]) -> int:
    for field in fields:
        if match(s, field[0]):
            return field[1]
    return 0


def get_fields(wait: WebDriverWait, fields_xpath: str) -> list[list]:
    columns = find_elements(wait, fields_xpath)
    idx = []
    if columns:
        for i, col in enumerate(columns, start=1):
            name = col.text.lower().strip()
            idx.append([name, i])
    return idx


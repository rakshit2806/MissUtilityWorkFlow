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


def _state_selects(driver: WebDriver) -> list:
    """Return <select> elements that look like the state picker (have an MD/DC style option)."""
    from selenium.webdriver.support.ui import Select
    found = []
    for sel in driver.find_elements(By.TAG_NAME, "select"):
        try:
            texts = [o.text.strip() for o in Select(sel).options]
        except Exception:
            continue
        if any(t.upper().startswith(("MD", "DC", "DE ", "VA")) or "SHORE" in t.upper() or "COLUMBIA" in t.upper() for t in texts):
            found.append((sel, texts))
    return found


def set_state(driver: WebDriver, state: str = "DC", timeout: int = 120) -> bool:
    """On the My Tickets page, change the state dropdown (e.g. 'MD - Western Shore') to the given state."""
    from time import time, sleep as _sleep
    from selenium.webdriver.support.ui import Select
    tickets_url = "https://md.itic.occinc.com/excavatorTickets"
    if "excavatorTickets" not in driver.current_url:
        driver.get(tickets_url)

    end = time() + timeout
    selects = []
    while time() < end:
        selects = _state_selects(driver)
        if selects:
            break
        _sleep(3)
    print(f"page: {driver.current_url} | state dropdowns found: {len(selects)}")
    for sel, texts in selects:
        print(f"  dropdown id={sel.get_attribute('id')!r} name={sel.get_attribute('name')!r} options={texts}")

    if not selects:
        print("WARNING: no state dropdown found. All dropdowns on page:")
        for sel in driver.find_elements(By.TAG_NAME, "select"):
            try:
                print(f"  id={sel.get_attribute('id')!r} options={[o.text for o in Select(sel).options][:40]}")
            except Exception:
                pass
        return False

    def current_states():
        out = []
        for sel2, _ in _state_selects(driver):
            try:
                out.append(Select(sel2).first_selected_option.text.strip())
            except Exception:
                pass
        return out

    # Use dropdowns that actually contain the target state
    candidates = [(sel, texts) for sel, texts in selects if any(_is_state_match(t, state) for t in texts)]
    if not candidates:
        print(f"WARNING: no dropdown has a {state!r} option")
        return False
    sel, texts = candidates[0]
    sel_id = sel.get_attribute("id")
    sel_name = sel.get_attribute("name") or sel_id or "selState"
    target = next(t for t in texts if _is_state_match(t, state))
    opt_value = next((o.get_attribute("value") for o in Select(sel).options if o.text.strip() == target), target)
    form_action = driver.execute_script("return arguments[0].form ? arguments[0].form.action + ' [' + arguments[0].form.method + ']' : null;", sel)
    print(f"using dropdown {sel_id!r}: option {target!r} value={opt_value!r} onchange={sel.get_attribute('onchange')!r} form={form_action!r}")
    print(f"dropdown html: {(sel.get_attribute('outerHTML') or '')[:600]}")

    def done():
        _sleep(8)
        now = current_states()
        print(f"  url now: {driver.current_url} | dropdowns show: {now}")
        return any(_is_state_match(t, state) for t in now)

    # Attempt 1: normal selection (fires the page's change handler)
    try:
        Select(sel).select_by_value(opt_value)
        print("attempt 1: selected via Selenium")
    except Exception as e:
        print(f"attempt 1 failed: {e}")
    if done():
        return True

    # Attempt 2: set value with JavaScript and fire change through jQuery and natively
    try:
        sel = driver.find_element(By.ID, sel_id)
        driver.execute_script("""
            var s = arguments[0], v = arguments[1];
            s.value = v;
            if (window.jQuery) { jQuery(s).val(v).trigger('change'); }
            s.dispatchEvent(new Event('change', {bubbles: true}));
        """, sel, opt_value)
        print("attempt 2: set via JavaScript + change event")
    except Exception as e:
        print(f"attempt 2 failed: {e}")
    if done():
        return True

    # Attempt 3: submit the form the dropdown belongs to
    try:
        sel = driver.find_element(By.ID, sel_id)
        submitted = driver.execute_script("""
            var s = arguments[0], v = arguments[1];
            s.value = v;
            if (s.form) { s.form.submit(); return true; } return false;
        """, sel, opt_value)
        print(f"attempt 3: form submit -> {submitted}")
    except Exception as e:
        print(f"attempt 3 failed: {e}")
    if done():
        return True

    # Attempt 4: call the set-state page directly
    from urllib.parse import quote
    name = sel_name
    for url in [
        f"https://md.itic.occinc.com/excavatorSetState?{quote(name or 'selState')}={quote(opt_value)}",
        f"https://md.itic.occinc.com/excavatorSetState?state={quote(opt_value)}",
    ]:
        try:
            driver.get(url)
            print(f"attempt 4: opened {url}")
            _sleep(4)
            if "excavatorTickets" not in driver.current_url:
                driver.get(tickets_url)
            if done():
                return True
        except Exception as e:
            print(f"attempt 4 failed for {url}: {e}")

    print(f"WARNING: could not switch state to {state!r}")
    return False


def show_all_entries(driver: WebDriver, table_id: str = "ExcavatorTicketTable", timeout: int = 300) -> None:
    """Make the ticket table show every entry on one page instead of 10 per page."""
    from time import time, sleep as _sleep
    from selenium.webdriver.support.ui import Select

    def info():
        try:
            return driver.find_element(By.ID, f"{table_id}_info").text.strip()
        except Exception:
            return ""

    print(f"before: {info()!r}")
    done = False
    # 1) DataTables API: page length -1 means 'All'
    try:
        done = driver.execute_script("""
            var id = '#' + arguments[0];
            if (window.jQuery && jQuery.fn.dataTable && jQuery.fn.dataTable.isDataTable(id)) {
                jQuery(id).DataTable().page.len(-1).draw();
                return true;
            }
            return false;
        """, table_id)
        print(f"set page length via DataTables API: {done}")
    except Exception as e:
        print(f"DataTables API failed: {e}")

    # 2) Fallback: pick the largest option in the 'Show N entries' dropdown
    if not done:
        try:
            sel = driver.find_element(By.XPATH, f"//select[@name='{table_id}_length'] | //div[@id='{table_id}_length']//select")
            s = Select(sel)
            vals = [o.get_attribute("value") for o in s.options]
            best = "-1" if "-1" in vals else max(vals, key=lambda v: int(v) if v.lstrip("-").isdigit() else 0)
            s.select_by_value(best)
            print(f"set 'Show entries' to {best!r} (options {vals})")
        except Exception as e:
            print(f"could not change 'Show entries': {e}")

    # Wait until the info text says it is showing everything (e.g. 'Showing 1 to 750 of 750 entries')
    import re as _re
    end = time() + timeout
    while time() < end:
        m = _re.search(r"to\s+([\d,]+)\s+of\s+([\d,]+)", info())
        if m and m.group(1) == m.group(2):
            break
        _sleep(5)
    print(f"after: {info()!r}")


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


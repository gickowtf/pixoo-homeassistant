import json
import requests

# Official Divoom docs: https://docin.divoom-gz.com/web/#/5/27


def main():
    dial_types = requests.post("https://app.divoom-gz.com/Channel/GetDialType").json()["DialTypeList"]

    for dial_type in dial_types:
        amount = 30
        curr_page = 1
        clock_ids = {}  # type: dict[int, str]

        while amount == 30:
            response = requests.post("https://app.divoom-gz.com/Channel/GetDialList", json.dumps({
                "DialType": dial_type,
                "Page": curr_page
            })).json()
            amount = len(response["DialList"])
            curr_page += 1
            for dial in response["DialList"]:
                clock_ids[dial["ClockId"]] = dial["Name"]

        if len(clock_ids) > 0:
            print("--------------")
            print("###", dial_type)
            ordered_clock_ids = dict(sorted(clock_ids.items()))
            for clock_id, name in ordered_clock_ids.items():
                print(f"- {clock_id}: {name}")


if __name__ == "__main__":
    main()
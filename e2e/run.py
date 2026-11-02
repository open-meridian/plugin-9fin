"""`make e2e`: the plugin on the plugin harness of the runtime it pins
(contract v29), beside `reader`, a reporting plugin (e2e/reader.py) entitled
to its dataset, and the harness's admin. Run from the repository's root by
the Makefile; standard library only. The harness's stand-in for the platform
mints a corporate bond by its FIGI (BBG01BOND0001) and knows Apple Inc.'s
CIK.

No 9fin credential is used: 9fin's API answers nowhere (the e2e's hosts
file), and sample data answers from the answers committed with the plugin.

1. No credential: Connection says "No key", and nothing is recorded.
2. Sample data on, four bonds and a loan listed: the bonds resolved, the
   loan said and not resolved.
3. Parity: through the deployment's MCP, `read_connection` answers what the
   page shows -- the corporate's platform record, its issuer's `ENT-` by its
   CIK, its terms offered -- and `read_datasets` the one dataset; core's
   `dashboard__list_datasets` lists it as declared.
4. The lake holds the four bonds' issue prices, and no loan's.
5. Licensed and entitled, the reader reads the corporate's issue price:
   99.812, kind last, dated its pricing date, 2 February 2026.
"""

import json
import os
import subprocess
import sys
import time

PROJECT = "ninefin-e2e"
LOG = ".e2e/runner.log"
COMPONENTS = ".e2e/components.log"
COMPOSE = ["docker", "compose", "-p", PROJECT, "-f", ".e2e/harness/compose.yaml",
           "-f", ".e2e/harness/plugins.yaml", "-f", "e2e/plugin.yaml"]
INSTANCE = "ninefin"
PRICES = f"{INSTANCE}:new_issue_prices"
APPLE = "US037833ER75"
LOAN = "US30161NAC72"
LISTED = [APPLE, "US30161NAA17", "USU3016NAA43", "US30161NAB99", LOAN]
APPLE_COMPANY = "ENT-01JC28APPLEINC000000000001"


class Failed(Exception):
    pass


def log(text):
    with open(LOG, "a", encoding="utf-8") as kept:
        kept.write(text + "\n")


def compose(*args, check=True, timeout=600):
    done = subprocess.run(COMPOSE + list(args), capture_output=True, text=True,
                          timeout=timeout)
    log(f"$ compose {' '.join(args)[:300]}\n{done.stdout[-4000:]}{done.stderr[-2000:]}")
    if check and done.returncode != 0:
        raise Failed(f"compose {' '.join(args)[:200]}: {(done.stdout + done.stderr).strip()[-600:]}")
    return done


def runner(*args, check=True):
    done = compose("run", "--rm", "-T", "runner", *args, check=check)
    return done.stdout if check else done


def must(condition, why):
    if not condition:
        raise Failed(why)


def until(seconds, attempt, what):
    deadline = time.monotonic() + seconds
    last = None
    while True:
        try:
            answer = attempt()
        except Failed as failed:
            answer, last = None, failed
        if answer:
            return answer
        if time.monotonic() > deadline:
            raise Failed(f"{what}, in {seconds} seconds" + (f": {last}" if last else ""))
        time.sleep(2)


def page(instance, level, path):
    said = runner("page", "--instance", instance, "--level", level, path)
    status, _, body = said.partition("\n")
    must(status.strip() == "200", f"{instance} {path} answered {said[-600:]}")
    return body


def call(tool, arguments=None):
    done = runner("mcp", "call", tool, json.dumps(arguments or {}), check=False)
    try:
        answer = json.loads(done.stdout)
    except ValueError:
        raise Failed(f"{tool}: no answer: {(done.stdout + done.stderr)[-400:]}")
    must(answer.get("outcome") in ("read", "unchanged"), f"{tool} answered {done.stdout[-700:]}")
    return answer["data"]


def store_lake():
    return compose("run", "--rm", "-T", "store", "lake").stdout


def reader(path):
    return json.loads(page("reader", "read", path))


def run():
    started = time.time()
    compose("--profile", "runner", "down", "-v", "--remove-orphans", check=False)
    compose("up", "-d")
    runner("ready")
    runner("ready", "--instance", "reader")

    # 1. No credential.
    runner("page", "--level", "admin", "/", "--until", "No key", "--seconds", "90")
    must("row|" not in store_lake(), "step 1, nothing recorded without a credential")

    # 2. Sample data, four bonds and a loan.
    runner("settings", "sample_data=true",
           *[f"securities[{n}].security={s}" for n, s in enumerate(LISTED)])
    runner("page", "--level", "admin", "/", "--until", "4 of 5 resolved", "--seconds", "180")

    # 3. Parity.
    runner("grant", "--level", "admin", "--role", "data")
    runner("mcp", "connect", "--covers", "deployment_admin", "--covers", f"{INSTANCE}:data:admin")
    tools = runner("mcp", "list").split()
    read_connection = next((t for t in tools if t.endswith("read_connection")), "")
    read_datasets = next((t for t in tools if t.endswith("read_datasets")), "")
    must(read_connection and read_datasets, f"step 3, the plugin's two tools are listed: {tools}")
    connection = call(read_connection)
    held = {s["security"]: s for s in connection["securities"]}
    apple = held.get(APPLE, {})
    must(connection["mode"] == "Sample data"
         and apple.get("record", "").startswith("INS-") and apple.get("issuer") == APPLE_COMPANY
         and apple.get("offered", 0) >= 5
         and held.get(LOAN, {}).get("miss") == "a loan: no template in v29",
         f"step 3, read_connection: {connection}")
    bond = apple["record"]
    datasets = call(read_datasets)
    must([s["dataset"] for s in datasets["served"]] == [PRICES], f"step 3, read_datasets: {datasets}")
    listed = {d["dataset"]: d for d in call("dashboard__list_datasets")["datasets"]}
    entry = listed.get(PRICES, {}).get("catalogue_entry", {})
    must(entry.get("modes") == ["push", "pull"], f"step 3, core lists {PRICES}: {listed.get(PRICES)}")

    # 4. The lake: four issue prices.
    def keys():
        return {line.split("|")[4] for line in store_lake().splitlines()
                if line.startswith(f"row|{PRICES}|price|")}

    found = until(120, lambda: (lambda k: k if len(k) == 4 else None)(keys()),
                  "step 4, the four bonds' issue prices were not recorded")
    must(f"9fin:issue:{LOAN}" not in found, f"step 4, no loan's price: {found}")

    # 5. Licensed and entitled: the corporate's issue price.
    runner("licence", PRICES, "kept=true", "retention_days=0", "derived_use=false",
           "display=true", "personal_use=false", "note=9fin's agreement, as the deployment's.")
    runner("entitle", "--instance", "reader", PRICES, "note=The e2e's reader reads them.")
    runner("grant", "--instance", "reader", "--level", "read")
    read = until(90, lambda: (lambda r: r if r["prices"] == 1 else None)(
        reader(f"/prices?subject={bond}&dataset={PRICES}")),
        "step 5, the corporate's issue price was not read")
    [price] = read["rows"]
    must(price["kind"] == "PRICE_KIND_LAST" and price["amount"] in ("99.812", "99.812000000")
         and price["currency"] == "USD" and price["business_date"] == "2026-02-02",
         f"step 5, the issue price as 9fin states it: {price}")

    print(f"e2e OK in {int(time.time() - started)}s on the plugin harness: no credential said and "
          f"nothing recorded; four bonds resolved and the loan said, the corporate to the "
          f"platform's record with its issuer {APPLE_COMPANY} by CIK and its terms offered; "
          f"read_connection and read_datasets answering what the pages show; four issue prices "
          f"in the lake, no loan's; and the corporate's read back, 99.812 on 2 February 2026")


def main():
    os.makedirs(".e2e", exist_ok=True)
    open(LOG, "w").close()
    try:
        run()
    except (Failed, subprocess.TimeoutExpired, KeyError, ValueError, IndexError, TypeError) as failed:
        with open(COMPONENTS, "a", encoding="utf-8") as kept:
            kept.write(compose("logs", "--no-color", check=False).stdout)
        compose("--profile", "runner", "down", "-v", "--remove-orphans", check=False)
        print(f"e2e FAILED: {failed}; the runner's log is in {LOG}, the components' in {COMPONENTS}",
              file=sys.stderr)
        return 1
    compose("--profile", "runner", "down", "-v", "--remove-orphans", check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())

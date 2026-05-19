import time

class BudgetTracker:
    def __init__(self, budget):
        self.start_ts = time.time()
        self.counters = {
            "tool_calls": 0,
            "pages": 0,
            "tokens": 0,
        }
        self._visited_urls = set()
        self._cancelled = False
        self.budget = budget

    def check_before_call(self, tool_name, tool_input):
        if self._cancelled:
            raise BudgetExceeded("Budget has been cancelled")

        elapsed = time.time() - self.start_ts
        if elapsed > self.budget["wall_clock"]:
            raise BudgetExceeded("Wall clock time exceeded")

        if self.counters["tool_calls"] >= self.budget["tool_calls"]:
            raise BudgetExceeded("Tool call limit exceeded")

        if tool_name == "browser_goto":
            url = tool_input.get("url", "")
            if url in self._visited_urls:
                raise BudgetExceeded(f"URL {url} has already been visited")
            if self.counters["pages"] >= self.budget["pages"]:
                raise BudgetExceeded("Page limit exceeded")
            
        # Token counting is approximate and happens after the call, so we don't check it here.
    def record_call(self, tool_name, tool_input, tool_output, tokens_used):
        self.counters["tool_calls"] += 1
        if tool_name == "browser_goto":
            url = tool_input.get("url", "")
            self._visited_urls.add(url)
            self.counters["pages"] += 1
        self.counters["tokens"] += tokens_used
    def cancel(self):
        self._cancelled = True

class BudgetExceeded(Exception):
    pass



/**
 * Current implementation is based on last 100 queries saved in local storage.
 */

function getSearchHistory() {
  const history = localStorage.getItem("searchHistory");
  if (history) {
    return JSON.parse(history);
  }
  return [];
}

function saveSearchHistory(history: string[]) {
  localStorage.setItem("searchHistory", JSON.stringify(history));
}

export async function addToSearchHistory(search: string) {
  const history = getSearchHistory();
  if (history.length > 0 && history[0] === search) {
    return;
  }

  const index = history.indexOf(search);
  if (index > -1) {
    history.splice(index, 1);
  }

  history.unshift(search);
  if (history.length > 100) {
    history.pop();
  }

  saveSearchHistory(history);
}

export function getSearchHistorySuggestions(search: string) {
  const history = getSearchHistory();
  return history
    .filter((item) => item.startsWith(search))
    .map((item) => item.slice(search.length))
    .slice(0, 6);
}
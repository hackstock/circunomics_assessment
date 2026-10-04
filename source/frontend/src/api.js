async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  let body = null;
  const text = await response.text();
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = { detail: text };
    }
  }
  if (!response.ok) {
    const detail = body?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg || JSON.stringify(item)).join("; ")
      : detail || `Request failed (${response.status})`;
    const error = new Error(message);
    error.status = response.status;
    error.body = body;
    throw error;
  }
  return body;
}

export function listRepositories() {
  return request("/api/repositories");
}

export function addRepository(fullName) {
  return request("/api/repositories", {
    method: "POST",
    body: JSON.stringify({ full_name: fullName }),
  });
}

export function syncRepository(id) {
  return request(`/api/repositories/${id}/sync`, { method: "POST" });
}

export function getRepository(id) {
  return request(`/api/repositories/${id}`);
}

export function listContributors(id, params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) {
      query.set(key, value);
    }
  });
  return request(`/api/repositories/${id}/contributors?${query}`);
}

export function listContributorCommits(id, key, params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([k, value]) => {
    if (value !== "" && value !== null && value !== undefined) {
      query.set(k, value);
    }
  });
  return request(`/api/repositories/${id}/contributors/${encodeURIComponent(key)}/commits?${query}`);
}

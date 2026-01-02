const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Types
interface CreateReviewRequest {
  code_content: string;
  language?: string;
  filename?: string;
}

interface CodeReview {
  id: number;
  code_content: string;
  language: string | null;
  filename: string | null;
  status: "pending" | "analyzing" | "completed" | "failed";
  created_at: string;
  updated_at: string;
}

interface ReviewComment {
  id: number;
  review_id: number;
  line_start: number;
  line_end: number;
  content: string;
  severity: string;
  category: string | null;
  suggestion: string | null;
  created_at: string;
}

interface ReviewResult {
  id: number;
  review_id: number;
  summary: string;
  issues_found: number;
  security_issues: number;
  quality_score: number | null;
  ai_model_used: string;
  processing_time_ms: number | null;
  created_at: string;
}

interface CodeReviewDetail extends CodeReview {
  comments: ReviewComment[];
  result: ReviewResult | null;
}

interface ReviewListResponse {
  items: CodeReview[];
  total: number;
  page: number;
  page_size: number;
}

// GitHub types
interface GitHubInstallation {
  id: number;
  installation_id: number;
  account_login: string;
  account_type: string;
  account_avatar_url: string | null;
  created_at: string;
  updated_at: string;
  repositories: GitHubRepository[];
}

interface GitHubRepository {
  id: number;
  installation_id: number;
  repo_id: number;
  full_name: string;
  private: boolean;
  default_branch: string;
  language: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
}

interface RepoContentItem {
  name: string;
  path: string;
  type: string;
  size?: number;
  sha: string;
}

interface RepoContentsResponse {
  items: RepoContentItem[];
  path: string;
  ref: string | null;
}

interface FileContentResponse {
  content: string;
  path: string;
  sha: string;
  size: number;
  language: string | null;
}

interface PullRequestInfo {
  number: number;
  title: string;
  state: string;
  user_login: string;
  user_avatar: string | null;
  head_sha: string;
  head_ref: string;
  base_ref: string;
  created_at: string;
  updated_at: string;
  additions: number;
  deletions: number;
  changed_files: number;
  html_url: string;
}

interface PRReview {
  id: number;
  repository_id: number;
  pr_number: number;
  pr_title: string | null;
  head_sha: string;
  base_branch: string | null;
  head_branch: string | null;
  status: "pending" | "analyzing" | "completed" | "failed";
  review_id: number | null;
  github_review_id: number | null;
  issues_found: number;
  files_reviewed: number;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

interface ReviewFileRequest {
  path: string;
  ref?: string;
  use_complex_model?: boolean;
}

// API functions
async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

export const api = {
  // Create a new code review
  createReview: (data: CreateReviewRequest): Promise<CodeReview> =>
    fetchApi("/api/reviews", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // List all reviews
  listReviews: (page = 1, pageSize = 20): Promise<ReviewListResponse> =>
    fetchApi(`/api/reviews?page=${page}&page_size=${pageSize}`),

  // Get a specific review with details
  getReview: (id: number): Promise<CodeReviewDetail> =>
    fetchApi(`/api/reviews/${id}`),

  // Trigger analysis
  analyzeReview: (
    id: number,
    useComplexModel = false
  ): Promise<CodeReviewDetail> =>
    fetchApi(`/api/reviews/${id}/analyze`, {
      method: "POST",
      body: JSON.stringify({ use_complex_model: useComplexModel }),
    }),

  // Delete a review
  deleteReview: (id: number): Promise<{ message: string }> =>
    fetchApi(`/api/reviews/${id}`, {
      method: "DELETE",
    }),

  // GitHub API
  github: {
    // Sync installations from GitHub
    syncInstallations: (): Promise<{ message: string; installations: string[] }> =>
      fetchApi("/api/github/installations/sync", { method: "POST" }),

    // List all installations
    listInstallations: (): Promise<GitHubInstallation[]> =>
      fetchApi("/api/github/installations"),

    // List repositories
    listRepos: (installationId?: number): Promise<GitHubRepository[]> => {
      const params = installationId ? `?installation_id=${installationId}` : "";
      return fetchApi(`/api/github/repos${params}`);
    },

    // Get repository contents
    getRepoContents: (
      owner: string,
      repo: string,
      path = "",
      ref?: string
    ): Promise<RepoContentsResponse> => {
      const params = new URLSearchParams();
      if (path) params.set("path", path);
      if (ref) params.set("ref", ref);
      const queryString = params.toString();
      return fetchApi(
        `/api/github/repos/${owner}/${repo}/contents${queryString ? `?${queryString}` : ""}`
      );
    },

    // Get file content
    getFileContent: (
      owner: string,
      repo: string,
      path: string,
      ref?: string
    ): Promise<FileContentResponse> => {
      const params = new URLSearchParams({ path });
      if (ref) params.set("ref", ref);
      return fetchApi(`/api/github/repos/${owner}/${repo}/file?${params}`);
    },

    // Review a file
    reviewFile: (
      owner: string,
      repo: string,
      request: ReviewFileRequest
    ): Promise<{ review_id: number; message: string }> =>
      fetchApi(`/api/github/repos/${owner}/${repo}/review`, {
        method: "POST",
        body: JSON.stringify(request),
      }),

    // List pull requests
    listPullRequests: (
      owner: string,
      repo: string,
      state = "open"
    ): Promise<PullRequestInfo[]> =>
      fetchApi(`/api/github/repos/${owner}/${repo}/pulls?state=${state}`),

    // List PR reviews
    listPRReviews: (
      owner: string,
      repo: string,
      prNumber: number
    ): Promise<PRReview[]> =>
      fetchApi(`/api/github/repos/${owner}/${repo}/pulls/${prNumber}/reviews`),

    // Trigger PR review
    reviewPullRequest: (
      owner: string,
      repo: string,
      prNumber: number,
      useComplexModel = false
    ): Promise<PRReview> =>
      fetchApi(`/api/github/repos/${owner}/${repo}/pulls/${prNumber}/review`, {
        method: "POST",
        body: JSON.stringify({ pr_number: prNumber, use_complex_model: useComplexModel }),
      }),
  },
};

export type AdminUser = {
  id: string;
  username: string;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
  enabled: boolean;
  roles: string[];
};

export type AdminUserListResponse = {
  items: AdminUser[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type CreateUserInput = {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: "user" | "admin";
  temporary_password: string;
};

export type DashboardStats = {
  total: number;
  completed: number;
  in_progress: number;
  failed: number;
  recent: ResumeSummary[];
};
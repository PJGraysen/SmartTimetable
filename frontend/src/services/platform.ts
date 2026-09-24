import http from "./http";

export type PlatformUser = {
  id: number;
  username: string;
  display_name: string;
  is_superuser: boolean;
};

export type PlatformApplication = {
  slug: string;
  name: string;
  description: string;
  entry_path: string;
  icon: string;
};

export type PlatformAuthResponse = {
  user: PlatformUser | null;
  applications: PlatformApplication[];
};

export async function login(username: string, password: string) {
  const response = await http.post<PlatformAuthResponse>(
    "/platform/auth/login/",
    { username, password },
  );
  return response.data;
}

export async function logout() {
  const response = await http.post("/platform/auth/logout/");
  return response.data;
}

export async function getMe() {
  const response = await http.get<PlatformAuthResponse>(
    "/platform/auth/me/",
  );
  return response.data;
}

export async function getApplications() {
  const response = await http.get<{ applications: PlatformApplication[] }>(
    "/platform/applications/",
  );
  return response.data;
}

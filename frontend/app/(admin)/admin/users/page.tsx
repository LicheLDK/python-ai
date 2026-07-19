import { UsersAdminPanel } from "@/components/admin/UsersAdminPanel";

export default function AdminUsersPage() {
  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Admin · Users</h1>
      <p style={{ color: "#4b5563", marginTop: 0 }}>
        검색 · role/status/name 변경 (audit 기록)
      </p>
      <UsersAdminPanel />
    </div>
  );
}

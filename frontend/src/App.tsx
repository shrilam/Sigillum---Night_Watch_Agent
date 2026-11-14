import { useDashboardData } from "./hooks/useDashboardData";
import { DashboardPage } from "./pages/DashboardPage";

export default function App() {
  const dashboardData = useDashboardData();
  return <DashboardPage {...dashboardData} />;
}

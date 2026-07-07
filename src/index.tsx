import { definePlugin } from "@decky/api";
import { staticClasses } from "@decky/ui";

export default definePlugin(() => ({
  name: "Lyall Fixes",
  titleView: <div className={staticClasses.Title}>Lyall Fixes</div>,
  content: <div>Loading…</div>,
  icon: <span>🔧</span>,
}));

import { useEffect, useState } from "react";
import { io } from "socket.io-client";

export default function useNotifications(userId) {
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    if (!userId) return;
    const socketUrl =
      process.env.NEXT_PUBLIC_NOTIFICATION_SOCKET_URL || window.location.origin;

    const socket = io(socketUrl, {
      query: { userId },
    });

    socket.on("notification", (data) => {
      setNotifications(prev => [data, ...prev]);
    });

    return () => socket.disconnect();
  }, [userId]);

  return notifications;
}

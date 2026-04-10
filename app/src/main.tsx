import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router";
import AppLayout from "./ui/layout/AppLayout";
import PapersView from "./ui/views/PapersView";
import ReviewView from "./ui/views/ReviewView";
import "./index.css";

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <PapersView /> },
      { path: "papers", element: <PapersView /> },
      { path: "review", element: <ReviewView /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
);

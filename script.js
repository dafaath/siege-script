import http from "k6/http";
import { sleep } from "k6";

export default function () {
  http.get("http://localhost:3000/node", {
    headers: {
      "Content-Type": "application/json",
      Accept: "/*/",
      "Accept-Encoding": "gzip, deflate, br",
      "Accept-Language": "en-US,en;q=0.9",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      Authorization:
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImFkbWluQGV4YW1wbGUuY29tIiwiaWF0IjoxNjc4MzMwMTI0LCJpZFVzZXIiOjEsImlzQWRtaW4iOnRydWUsInN0YXR1cyI6dHJ1ZSwidXNlcm5hbWUiOiJhZG1pbiJ9.VWTfuPlXuRDW_-uTh7lOC7URwnPfiMJDqAJXa3tCTCQ",
    },
  });
  sleep(1);
}

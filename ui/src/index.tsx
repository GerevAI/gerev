import * as React from "react";
import * as ReactDOM from "react-dom";
import './assets/css/index.css';
import App from './App';
import { PostHogProvider} from 'posthog-js/react'
import posthog from 'posthog-js';

posthog.init(
  "phc_unIQdP9MFUa5bQNIKy5ktoRCPWMPWgqTbRvZr4391Pm",
  {
    api_host: "https://eu.posthog.com",
    disable_session_recording: true,
    autocapture: false,
    enable_recording_console_log: false,
  }
);

ReactDOM.render(
  <PostHogProvider client={posthog}>
      <App />
  </PostHogProvider>,
    document.getElementById("root")
);

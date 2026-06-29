/**
 * Twilio Function: whatsapp-in
 * Deployed at: whatsapp-in-<id>.twil.io  (Twilio Console > Functions & Assets)
 *
 * The inbound bridge between Twilio WhatsApp and the UiPath Maestro case.
 * Twilio invokes this on every inbound WhatsApp message; it repackages the
 * Twilio form fields into JSON and POSTs them to the UiPath HTTP Webhook that
 * triggers Foreman-Dispatcher (which starts the Maestro "Agentic case").
 *
 * Environment Variable required (Twilio Console > Functions > Environment Variables):
 *   UIPATH_WEBHOOK_URL = the Foreman-Dispatcher HTTP Webhook URL from UiPath
 *                        (Studio > foremen v1 > Foreman-Dispatcher > HTTP Webhook trigger)
 *
 * NOTE: This file mirrors the function deployed in the Twilio Console. If you
 * change the deployed version, update this copy so the repo stays in sync.
 */
exports.handler = function (context, event, callback) {
  const https = require('https');

  // Twilio sends these as form fields on every inbound WhatsApp message:
  const payload = JSON.stringify({
    from:             event.From,             // e.g. "whatsapp:+917225865778"
    body:             event.Body || "",
    numMedia:         event.NumMedia || "0",
    mediaUrl:         event.MediaUrl0 || "",  // full Twilio media URL (only if NumMedia > 0)
    messageSid:       event.MessageSid,
    mediaContentType: event.MediaContentType0,
  });

  const url = new URL(context.UIPATH_WEBHOOK_URL);
  const options = {
    hostname: url.hostname,
    path: url.pathname + url.search,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(payload),
    },
  };

  const req = https.request(options, (res) => {
    let data = '';
    res.on('data', (chunk) => { data += chunk; });
    res.on('end', () => {
      console.log('UiPath webhook responded:', res.statusCode, data);
      // Return an empty TwiML response so Twilio does not auto-reply.
      const twiml = new Twilio.twiml.MessagingResponse();
      callback(null, twiml);
    });
  });

  req.on('error', (err) => {
    console.error('Error POSTing to UiPath webhook:', err);
    callback(err);
  });

  req.write(payload);
  req.end();
};

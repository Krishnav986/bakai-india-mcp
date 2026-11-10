package com.bakai.phoneconnect;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.ContactsContract;
import android.graphics.Typeface;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {

    private static final int CONTACT_PERMISSION = 100;

    private static final String GATEWAY_URL =
            "https://cautious-guacamole-6vpvwq5jpgrpf4p5g-8765.app.github.dev";

    private EditText tokenBox;
    private EditText searchBox;
    private TextView connectionStatus;
    private TextView requestStatus;
    private LinearLayout results;

    private final Handler mainHandler =
            new Handler(Looper.getMainLooper());

    private final ExecutorService networkExecutor =
            Executors.newCachedThreadPool();

    private volatile boolean shouldPoll = false;
    private volatile String gatewayToken = "";
    private volatile String pendingRequestId = null;
    private volatile String pendingQuery = "";

    private boolean connectionRequested = false;
    private Thread pollingThread;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        buildInterface();
    }

    @Override
    protected void onStart() {
        super.onStart();

        if (connectionRequested && !shouldPoll) {
            startPolling();
        }
    }

    @Override
    protected void onStop() {
        super.onStop();

        shouldPoll = false;
        setConnectionText("Paused — reopen the app to reconnect");
    }

    @Override
    protected void onDestroy() {
        shouldPoll = false;
        networkExecutor.shutdownNow();
        super.onDestroy();
    }

    private void buildInterface() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(24, 30, 24, 20);
        root.setBackgroundColor(0xFFF5F6FA);

        TextView title = new TextView(this);
        title.setText("BAKAI Phone Connect");
        title.setTextSize(25);
        title.setTypeface(null, Typeface.BOLD);
        title.setTextColor(0xFF172554);
        root.addView(title);

        connectionStatus = new TextView(this);
        connectionStatus.setText("Offline");
        connectionStatus.setTextSize(15);
        connectionStatus.setTypeface(null, Typeface.BOLD);
        connectionStatus.setTextColor(0xFFB91C1C);
        connectionStatus.setPadding(0, 12, 0, 12);
        root.addView(connectionStatus);

        tokenBox = new EditText(this);
        tokenBox.setSingleLine(true);
        tokenBox.setHint("Enter PHONE_GATEWAY_TOKEN");
        tokenBox.setInputType(
                InputType.TYPE_CLASS_TEXT
                        | InputType.TYPE_TEXT_VARIATION_PASSWORD
        );
        root.addView(tokenBox);

        Button connectButton = new Button(this);
        connectButton.setText("Connect to BAKAI");
        root.addView(connectButton);

        connectButton.setOnClickListener(v -> {
            if (shouldPoll) {
                connectionRequested = false;
                shouldPoll = false;
                setConnectionText("Offline");
                connectButton.setText("Connect to BAKAI");
                return;
            }

            String enteredToken =
                    tokenBox.getText().toString().trim();

            if (enteredToken.isEmpty()) {
                Toast.makeText(
                        this,
                        "Enter your gateway token first",
                        Toast.LENGTH_SHORT
                ).show();
                return;
            }

            gatewayToken = enteredToken;
            connectionRequested = true;
            connectButton.setText("Disconnect");
            startPolling();
        });

        TextView divider = new TextView(this);
        divider.setText("CONTACT SEARCH");
        divider.setTextSize(13);
        divider.setTypeface(null, Typeface.BOLD);
        divider.setTextColor(0xFF475569);
        divider.setPadding(0, 20, 0, 8);
        root.addView(divider);

        searchBox = new EditText(this);
        searchBox.setSingleLine(true);
        searchBox.setHint("Enter a contact name or number");
        root.addView(searchBox);

        Button searchButton = new Button(this);
        searchButton.setText("Search contacts");
        root.addView(searchButton);

        searchButton.setOnClickListener(v ->
                requestContactAccess(searchBox.getText().toString().trim())
        );

        requestStatus = new TextView(this);
        requestStatus.setText("No pending contact request.");
        requestStatus.setTextSize(14);
        requestStatus.setTextColor(0xFF1E40AF);
        requestStatus.setPadding(0, 16, 0, 10);
        root.addView(requestStatus);

        TextView privacy = new TextView(this);
        privacy.setText(
                "Contacts are searched locally. Only a contact you "
                        + "explicitly select is shared with BAKAI. "
                        + "Calls are never placed automatically."
        );
        privacy.setTextSize(12);
        privacy.setTextColor(0xFF475569);
        privacy.setPadding(0, 4, 0, 12);
        root.addView(privacy);

        ScrollView scroll = new ScrollView(this);

        results = new LinearLayout(this);
        results.setOrientation(LinearLayout.VERTICAL);

        scroll.addView(results);

        root.addView(
                scroll,
                new LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT,
                        0,
                        1
                )
        );

        setContentView(root);
    }

    private void setConnectionText(String message) {
        mainHandler.post(() -> {
            if (connectionStatus == null) return;

            connectionStatus.setText(message);

            if (message.startsWith("Online")) {
                connectionStatus.setTextColor(0xFF15803D);
            } else {
                connectionStatus.setTextColor(0xFFB91C1C);
            }
        });
    }

    private void startPolling() {
        if (shouldPoll) return;

        shouldPoll = true;
        setConnectionText("Connecting...");

        pollingThread = new Thread(this::pollLoop);
        pollingThread.start();
    }

    private void pollLoop() {
        while (shouldPoll) {
            try {
                String health = httpRequest(
                        "/phone/health",
                        "GET",
                        null
                );

                JSONObject healthJson = new JSONObject(health);

                if (!"online".equals(healthJson.optString("status"))) {
                    throw new Exception("Gateway is not online");
                }

                setConnectionText("Online — waiting for BAKAI");

                while (shouldPoll) {
                    String response = httpRequest(
                            "/phone/poll",
                            "GET",
                            null
                    );

                    JSONObject json = new JSONObject(response);

                    if (json.isNull("request")) {
                        continue;
                    }

                    JSONObject request = json.getJSONObject("request");

                    String id = request.optString("id", "");
                    String query = request.optString("query", "");

                    if (id.isEmpty() || query.isEmpty()) {
                        continue;
                    }

                    pendingRequestId = id;
                    pendingQuery = query;

                    mainHandler.post(() -> {
                        requestStatus.setText(
                                "BAKAI is requesting: " + query
                        );

                        searchBox.setText(query);

                        requestContactAccess(query);
                    });

                    // Wait until the user selects a contact.
                    while (shouldPoll && pendingRequestId != null) {
                        Thread.sleep(500);
                    }
                }

            } catch (Exception e) {
                if (shouldPoll) {
                    setConnectionText("Connection problem — retrying...");

                    try {
                        Thread.sleep(3000);
                    } catch (InterruptedException ignored) {
                        Thread.currentThread().interrupt();
                        return;
                    }
                }
            }
        }
    }

    private String httpRequest(
            String path,
            String method,
            JSONObject body
    ) throws Exception {

        HttpURLConnection connection = null;

        try {
            URL url = new URL(GATEWAY_URL + path);

            connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod(method);
            connection.setConnectTimeout(10000);
            connection.setReadTimeout(
                    path.equals("/phone/poll") ? 25000 : 10000
            );

            connection.setRequestProperty(
                    "Authorization",
                    "Bearer " + gatewayToken
            );

            connection.setRequestProperty(
                    "Accept",
                    "application/json"
            );

            if (body != null) {
                connection.setDoOutput(true);
                connection.setRequestProperty(
                        "Content-Type",
                        "application/json; charset=UTF-8"
                );

                try (OutputStream output = connection.getOutputStream()) {
                    output.write(
                            body.toString().getBytes(StandardCharsets.UTF_8)
                    );
                }
            }

            int status = connection.getResponseCode();

            InputStream stream = status >= 200 && status < 300
                    ? connection.getInputStream()
                    : connection.getErrorStream();

            if (stream == null) {
                throw new Exception("Gateway HTTP error: " + status);
            }

            StringBuilder response = new StringBuilder();

            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(stream, StandardCharsets.UTF_8)
            )) {
                String line;

                while ((line = reader.readLine()) != null) {
                    response.append(line);
                }
            }

            if (status < 200 || status >= 300) {
                throw new Exception("Gateway HTTP error: " + status);
            }

            return response.toString();

        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    private void requestContactAccess(String query) {
        if (checkSelfPermission(Manifest.permission.READ_CONTACTS)
                == PackageManager.PERMISSION_GRANTED) {
            searchContacts(query);
        } else {
            requestPermissions(
                    new String[]{Manifest.permission.READ_CONTACTS},
                    CONTACT_PERMISSION
            );
        }
    }

    @Override
    public void onRequestPermissionsResult(
            int requestCode,
            String[] permissions,
            int[] grantResults
    ) {
        super.onRequestPermissionsResult(
                requestCode,
                permissions,
                grantResults
        );

        if (requestCode == CONTACT_PERMISSION
                && grantResults.length > 0
                && grantResults[0] == PackageManager.PERMISSION_GRANTED) {

            String query = pendingQuery.isEmpty()
                    ? searchBox.getText().toString().trim()
                    : pendingQuery;

            searchContacts(query);

        } else if (requestCode == CONTACT_PERMISSION) {
            Toast.makeText(
                    this,
                    "Contact permission was not granted",
                    Toast.LENGTH_SHORT
            ).show();
        }
    }

    private void searchContacts(String query) {
        results.removeAllViews();

        if (query == null || query.trim().isEmpty()) {
            Toast.makeText(
                    this,
                    "Enter a name or number first",
                    Toast.LENGTH_SHORT
            ).show();
            return;
        }

        String selection =
                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME
                        + " LIKE ? OR "
                        + ContactsContract.CommonDataKinds.Phone.NUMBER
                        + " LIKE ?";

        String match = "%" + query.trim() + "%";

        try (Cursor cursor = getContentResolver().query(
                ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                new String[]{
                        ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                        ContactsContract.CommonDataKinds.Phone.NUMBER
                },
                selection,
                new String[]{match, match},
                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME + " ASC"
        )) {
            int count = 0;

            if (cursor != null) {
                while (cursor.moveToNext() && count < 30) {
                    String name = cursor.getString(0);
                    String number = cursor.getString(1);

                    if (name == null) name = "Unknown contact";
                    if (number == null) number = "";

                    addContact(name, number);
                    count++;
                }
            }

            if (count == 0) {
                TextView empty = new TextView(this);
                empty.setText("No matching contacts found.");
                empty.setPadding(0, 18, 0, 0);
                results.addView(empty);
            }

        } catch (Exception e) {
            Toast.makeText(
                    this,
                    "Could not read contacts",
                    Toast.LENGTH_SHORT
            ).show();
        }
    }

    private void addContact(String name, String number) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.VERTICAL);
        row.setPadding(8, 12, 8, 12);

        TextView details = new TextView(this);
        details.setText(name + "\n" + number);
        details.setTextSize(15);
        details.setTextColor(0xFF172554);
        row.addView(details);

        Button dialButton = new Button(this);
        dialButton.setText("Open dialler");
        dialButton.setOnClickListener(v -> {
            Intent dial = new Intent(
                    Intent.ACTION_DIAL,
                    Uri.fromParts("tel", number, null)
            );
            startActivity(dial);
        });
        row.addView(dialButton);

        if (pendingRequestId != null) {
            Button shareButton = new Button(this);
            shareButton.setText("Send selected contact to BAKAI");

            shareButton.setOnClickListener(v ->
                    sendContactToBakai(name, number)
            );

            row.addView(shareButton);
        }

        results.addView(row);

        View separator = new View(this);
        separator.setBackgroundColor(0xFFD1D5DB);

        results.addView(
                separator,
                new LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT,
                        1
                )
        );
    }

    private void sendContactToBakai(String name, String number) {
        String requestId = pendingRequestId;

        if (requestId == null) {
            Toast.makeText(
                    this,
                    "There is no pending BAKAI request",
                    Toast.LENGTH_SHORT
            ).show();
            return;
        }

        requestStatus.setText("Sending your selected contact...");

        networkExecutor.execute(() -> {
            try {
                JSONObject body = new JSONObject();
                body.put("id", requestId);
                body.put("name", name);
                body.put("number", number);

                String response = httpRequest(
                        "/phone/result",
                        "POST",
                        body
                );

                JSONObject json = new JSONObject(response);

                if (!"received".equals(json.optString("status"))) {
                    throw new Exception("Gateway did not accept the contact");
                }

                if (requestId.equals(pendingRequestId)) {
                    pendingRequestId = null;
                    pendingQuery = "";
                }

                mainHandler.post(() -> {
                    requestStatus.setText(
                            "Contact successfully sent to BAKAI."
                    );

                    Toast.makeText(
                            this,
                            "Contact sent to BAKAI",
                            Toast.LENGTH_SHORT
                    ).show();

                    searchContacts(searchBox.getText().toString().trim());
                });

            } catch (Exception e) {
                mainHandler.post(() -> {
                    requestStatus.setText(
                            "Could not send contact. Please try again."
                    );

                    Toast.makeText(
                            this,
                            "Contact sharing failed",
                            Toast.LENGTH_LONG
                    ).show();
                });
            }
        });
    }
}
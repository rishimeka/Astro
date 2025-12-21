import { Handler } from "@netlify/functions";

export const handler: Handler = async (event) => {
    try {
        if (event.httpMethod === "GET") {
            return {
                statusCode: 200,
                body: JSON.stringify({ message: "request-access function OK" }),
            };
        }

        if (event.httpMethod !== "POST") {
            return { statusCode: 405, body: "Method Not Allowed" };
        }

        const payload = event.body ? JSON.parse(event.body) : {};
        const email = payload?.email || payload?.emailAddress;

        if (!email) {
            return {
                statusCode: 400,
                body: JSON.stringify({ error: "Missing email" }),
            };
        }

        // Server-side only: enqueue or send notification here (do not expose client-side creds)
        console.log("request-access received for:", email);

        return {
            statusCode: 200,
            body: JSON.stringify({ message: "Request received" }),
        };
    } catch (err) {
        console.error(err);
        return { statusCode: 500, body: JSON.stringify({ error: "Internal error" }) };
    }
};

export default handler;

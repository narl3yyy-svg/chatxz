use axum::extract::ws::{Message, WebSocket};
use futures_util::{SinkExt, StreamExt};
use tokio_tungstenite::{connect_async, tungstenite::Message as TsMessage};
use tracing::warn;

/// Bidirectional relay: browser WebSocket ↔ Python backend /ws.
pub async fn relay_ui_ws(client: WebSocket, backend_http: String) {
    let ws_url = backend_http
        .trim_end_matches('/')
        .replace("http://", "ws://")
        .replace("https://", "wss://");
    let ws_url = format!("{ws_url}/ws");

    let backend = match connect_async(&ws_url).await {
        Ok((stream, _)) => stream,
        Err(e) => {
            warn!(%e, %ws_url, "backend ws connect failed");
            return;
        }
    };

    let (mut client_tx, mut client_rx) = client.split();
    let (mut backend_tx, mut backend_rx) = backend.split();

    let client_to_backend = async {
        while let Some(msg) = client_rx.next().await {
            match msg {
                Ok(Message::Text(text)) => {
                    if backend_tx.send(TsMessage::Text(text.to_string())).await.is_err() {
                        break;
                    }
                }
                Ok(Message::Binary(data)) => {
                    if backend_tx
                        .send(TsMessage::Binary(data.to_vec()))
                        .await
                        .is_err()
                    {
                        break;
                    }
                }
                Ok(Message::Ping(data)) => {
                    if backend_tx.send(TsMessage::Ping(data.to_vec())).await.is_err() {
                        break;
                    }
                }
                Ok(Message::Pong(data)) => {
                    if backend_tx.send(TsMessage::Pong(data.to_vec())).await.is_err() {
                        break;
                    }
                }
                Ok(Message::Close(_)) | Err(_) => break,
            }
        }
        let _ = backend_tx.close().await;
    };

    let backend_to_client = async {
        while let Some(msg) = backend_rx.next().await {
            match msg {
                Ok(TsMessage::Text(text)) => {
                    if client_tx.send(Message::Text(text.into())).await.is_err() {
                        break;
                    }
                }
                Ok(TsMessage::Binary(data)) => {
                    if client_tx.send(Message::Binary(data.into())).await.is_err() {
                        break;
                    }
                }
                Ok(TsMessage::Ping(data)) => {
                    if client_tx.send(Message::Ping(data.into())).await.is_err() {
                        break;
                    }
                }
                Ok(TsMessage::Pong(data)) => {
                    if client_tx.send(Message::Pong(data.into())).await.is_err() {
                        break;
                    }
                }
                Ok(TsMessage::Close(_)) | Err(_) => break,
                _ => {}
            }
        }
        let _ = client_tx.close().await;
    };

    tokio::select! {
        _ = client_to_backend => {}
        _ = backend_to_client => {}
    }
}
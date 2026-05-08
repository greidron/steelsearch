import java.io.ByteArrayOutputStream;
import java.net.InetSocketAddress;
import java.nio.ByteBuffer;
import java.nio.channels.SelectionKey;
import java.nio.channels.Selector;
import java.nio.channels.SocketChannel;
import java.util.Iterator;

public class MinimalSelectorHandshakeClient {
    private static byte[] hexToBytes(String hex) {
        String normalized = hex.replaceAll("\\s+", "");
        if ((normalized.length() & 1) != 0) {
            throw new IllegalArgumentException("hex length must be even");
        }
        byte[] out = new byte[normalized.length() / 2];
        for (int i = 0; i < out.length; i++) {
            int hi = Character.digit(normalized.charAt(i * 2), 16);
            int lo = Character.digit(normalized.charAt(i * 2 + 1), 16);
            if (hi < 0 || lo < 0) {
                throw new IllegalArgumentException("invalid hex digit");
            }
            out[i] = (byte) ((hi << 4) | lo);
        }
        return out;
    }

    private static String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) {
            sb.append(String.format("%02x", b & 0xff));
        }
        return sb.toString();
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 3 || args.length > 4) {
            System.err.println("usage: MinimalSelectorHandshakeClient <host> <port> <request_hex> [timeout_ms]");
            System.exit(2);
        }

        String host = args[0];
        int port = Integer.parseInt(args[1]);
        byte[] request = hexToBytes(args[2]);
        long timeoutMs = args.length == 4 ? Long.parseLong(args[3]) : 1000L;

        long startedAt = System.currentTimeMillis();
        boolean connectReady = false;
        boolean writeReady = false;
        boolean readReady = false;
        boolean connectFinished = false;
        int bytesWritten = 0;
        int bytesRead = 0;
        String exceptionClass = null;
        String exceptionMessage = null;
        ByteArrayOutputStream response = new ByteArrayOutputStream();

        try (Selector selector = Selector.open(); SocketChannel channel = SocketChannel.open()) {
            channel.configureBlocking(false);
            channel.connect(new InetSocketAddress(host, port));
            channel.register(selector, SelectionKey.OP_CONNECT);

            ByteBuffer writeBuffer = ByteBuffer.wrap(request);
            ByteBuffer readBuffer = ByteBuffer.allocate(4096);

            long deadline = startedAt + timeoutMs;
            while (System.currentTimeMillis() < deadline) {
                long remaining = Math.max(1L, deadline - System.currentTimeMillis());
                int selected = selector.select(remaining);
                if (selected == 0) {
                    continue;
                }

                Iterator<SelectionKey> it = selector.selectedKeys().iterator();
                while (it.hasNext()) {
                    SelectionKey key = it.next();
                    it.remove();
                    if (!key.isValid()) {
                        continue;
                    }

                    if (key.isConnectable()) {
                        connectReady = true;
                        SocketChannel sc = (SocketChannel) key.channel();
                        if (sc.finishConnect()) {
                            connectFinished = true;
                            key.interestOps(SelectionKey.OP_WRITE | SelectionKey.OP_READ);
                        }
                    }

                    if (key.isWritable() && writeBuffer.hasRemaining()) {
                        writeReady = true;
                        SocketChannel sc = (SocketChannel) key.channel();
                        bytesWritten += sc.write(writeBuffer);
                        if (!writeBuffer.hasRemaining()) {
                            key.interestOps(SelectionKey.OP_READ);
                        }
                    }

                    if (key.isReadable()) {
                        readReady = true;
                        SocketChannel sc = (SocketChannel) key.channel();
                        int n = sc.read(readBuffer);
                        if (n > 0) {
                            bytesRead += n;
                            readBuffer.flip();
                            byte[] chunk = new byte[readBuffer.remaining()];
                            readBuffer.get(chunk);
                            response.write(chunk);
                            readBuffer.clear();
                            deadline = System.currentTimeMillis();
                            break;
                        }
                        if (n < 0) {
                            deadline = System.currentTimeMillis();
                            break;
                        }
                    }
                }
            }
        } catch (Exception e) {
            exceptionClass = e.getClass().getName();
            exceptionMessage = e.getMessage();
        }

        long finishedAt = System.currentTimeMillis();
        System.out.println("{");
        System.out.println("  \"host\": \"" + host + "\",");
        System.out.println("  \"port\": " + port + ",");
        System.out.println("  \"timeout_ms\": " + timeoutMs + ",");
        System.out.println("  \"connect_ready\": " + connectReady + ",");
        System.out.println("  \"connect_finished\": " + connectFinished + ",");
        System.out.println("  \"write_ready\": " + writeReady + ",");
        System.out.println("  \"read_ready\": " + readReady + ",");
        System.out.println("  \"bytes_written\": " + bytesWritten + ",");
        System.out.println("  \"bytes_read\": " + bytesRead + ",");
        System.out.println("  \"response_hex\": \"" + bytesToHex(response.toByteArray()) + "\",");
        System.out.println("  \"duration_ms\": " + (finishedAt - startedAt) + ",");
        System.out.println("  \"exception_class\": " + (exceptionClass == null ? "null" : "\"" + exceptionClass + "\"") + ",");
        System.out.println("  \"exception_message\": " + (exceptionMessage == null ? "null" : "\"" + exceptionMessage.replace("\"", "'") + "\""));
        System.out.println("}");
    }
}

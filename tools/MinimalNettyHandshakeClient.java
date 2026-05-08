import io.netty.bootstrap.Bootstrap;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import io.netty.channel.ChannelFuture;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.ChannelInboundHandlerAdapter;
import io.netty.channel.ChannelInitializer;
import io.netty.channel.ChannelOption;
import io.netty.channel.ChannelPipeline;
import io.netty.channel.nio.NioEventLoopGroup;
import io.netty.channel.socket.SocketChannel;
import io.netty.channel.socket.nio.NioSocketChannel;

import java.io.ByteArrayOutputStream;
import java.net.InetSocketAddress;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

public class MinimalNettyHandshakeClient {
    private static final class State {
        boolean connectFinished;
        boolean channelActive;
        boolean writeSubmitted;
        boolean writeSuccess;
        boolean readObserved;
        int bytesWritten;
        int bytesRead;
        String exceptionClass;
        String exceptionMessage;
        final ByteArrayOutputStream response = new ByteArrayOutputStream();
        final CountDownLatch done = new CountDownLatch(1);
    }

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
            System.err.println("usage: MinimalNettyHandshakeClient <host> <port> <request_hex> [timeout_ms]");
            System.exit(2);
        }

        String host = args[0];
        int port = Integer.parseInt(args[1]);
        byte[] request = hexToBytes(args[2]);
        long timeoutMs = args.length == 4 ? Long.parseLong(args[3]) : 1000L;

        long startedAt = System.currentTimeMillis();
        State state = new State();

        NioEventLoopGroup group = new NioEventLoopGroup(1);
        try {
            Bootstrap bootstrap = new Bootstrap();
            bootstrap.group(group)
                .channel(NioSocketChannel.class)
                .option(ChannelOption.TCP_NODELAY, true)
                .handler(new ChannelInitializer<SocketChannel>() {
                    @Override
                    protected void initChannel(SocketChannel ch) {
                        ChannelPipeline pipeline = ch.pipeline();
                        pipeline.addLast(new ChannelInboundHandlerAdapter() {
                            @Override
                            public void channelActive(ChannelHandlerContext ctx) {
                                state.channelActive = true;
                                ByteBuf buf = Unpooled.wrappedBuffer(request);
                                state.bytesWritten = buf.readableBytes();
                                state.writeSubmitted = true;
                                ctx.writeAndFlush(buf).addListener(future -> {
                                    state.writeSuccess = future.isSuccess();
                                    if (!future.isSuccess() && state.exceptionClass == null) {
                                        Throwable t = future.cause();
                                        state.exceptionClass = t.getClass().getName();
                                        state.exceptionMessage = t.getMessage();
                                        state.done.countDown();
                                    }
                                });
                            }

                            @Override
                            public void channelRead(ChannelHandlerContext ctx, Object msg) {
                                state.readObserved = true;
                                ByteBuf buf = (ByteBuf) msg;
                                try {
                                    int n = buf.readableBytes();
                                    state.bytesRead += n;
                                    byte[] chunk = new byte[n];
                                    buf.readBytes(chunk);
                                    state.response.write(chunk, 0, chunk.length);
                                } finally {
                                    buf.release();
                                }
                                state.done.countDown();
                            }

                            @Override
                            public void exceptionCaught(ChannelHandlerContext ctx, Throwable cause) {
                                if (state.exceptionClass == null) {
                                    state.exceptionClass = cause.getClass().getName();
                                    state.exceptionMessage = cause.getMessage();
                                }
                                state.done.countDown();
                                ctx.close();
                            }
                        });
                    }
                });

            ChannelFuture connectFuture = bootstrap.connect(new InetSocketAddress(host, port)).sync();
            state.connectFinished = connectFuture.isSuccess();
            state.done.await(timeoutMs, TimeUnit.MILLISECONDS);
            connectFuture.channel().close().syncUninterruptibly();
        } catch (Exception e) {
            if (state.exceptionClass == null) {
                state.exceptionClass = e.getClass().getName();
                state.exceptionMessage = e.getMessage();
            }
        } finally {
            group.shutdownGracefully().syncUninterruptibly();
        }

        long finishedAt = System.currentTimeMillis();
        System.out.println("{");
        System.out.println("  \"host\": \"" + host + "\",");
        System.out.println("  \"port\": " + port + ",");
        System.out.println("  \"timeout_ms\": " + timeoutMs + ",");
        System.out.println("  \"connect_finished\": " + state.connectFinished + ",");
        System.out.println("  \"channel_active\": " + state.channelActive + ",");
        System.out.println("  \"write_submitted\": " + state.writeSubmitted + ",");
        System.out.println("  \"write_success\": " + state.writeSuccess + ",");
        System.out.println("  \"read_observed\": " + state.readObserved + ",");
        System.out.println("  \"bytes_written\": " + state.bytesWritten + ",");
        System.out.println("  \"bytes_read\": " + state.bytesRead + ",");
        System.out.println("  \"response_hex\": \"" + bytesToHex(state.response.toByteArray()) + "\",");
        System.out.println("  \"duration_ms\": " + (finishedAt - startedAt) + ",");
        System.out.println("  \"exception_class\": " + (state.exceptionClass == null ? "null" : "\"" + state.exceptionClass + "\"") + ",");
        System.out.println("  \"exception_message\": " + (state.exceptionMessage == null ? "null" : "\"" + state.exceptionMessage.replace("\"", "'") + "\""));
        System.out.println("}");
    }
}

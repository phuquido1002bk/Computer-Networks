# Computer-Network

Mở 2 terminal chạy song song nhau. 
- Terminal 1 đại diện cho SERVER chạy lệnh:
- python Server.py server_port
                
       + Server_port: cổng port mà SERVER chờ kết nối RTSP. Cổng RTSP tiêu chuẩn là 554, nhưng ta nên chọn cổng lớn hơn 1024.


- Terminal 2 đại diện cho CLIENT chạy lệnh:
- python ClientLauncher.py server_host server_port RTP_port video_file
                
        + Server_host: tên máy tính của bạn, hoặc địa chỉ IP của máy tính
        + Server_port: tên cổng port đã nhập ở terminal SERVER.
        + RTP_port: là cổng mà RTP packet được nhận.
        + Video_file: là tên video muốn chiếu.

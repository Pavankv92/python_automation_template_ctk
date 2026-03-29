import socket
import time
from enum import Enum, auto
from queue import Queue

from serial import Serial

from python_automation_template_ctk.logging_config import logger


class SerialInterface:
    def __init__(self, serial_port: int, baud_rate: int = 9600, *args, **kwargs):
        self.port = serial_port
        self.buad_rate = baud_rate

        try:
            # connect the serial port
            self.serial = Serial(port=self.port, baudrate=self.buad_rate)
            time.sleep(1)
        except Exception as e:
            logger.error(f"Serial error: {e}")
            return None

    def send_command(self, command: str, ending: str = "\r") -> None:
        full_command = command + ending
        self.serial.write(full_command.encode())
        time.sleep(0.2)

    def receive(self) -> bytes | None:
        return self.serial.read_all()

    def send_receive(self, command: str) -> bytes | None:
        self.send_command(command=command)
        return self.receive()

    def is_connected(self) -> bool:
        return self.serial is not None and self.serial.is_open

    def close(self) -> None:
        try:
            self.serial.close()
        except Exception as e:
            logger.error(f"Error while closing the Seiral: {e}")


class TCPInterface:
    def __init__(self, ip_address, port_num, *args, **kwargs) -> None:
        self.tcp = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        try:
            self.tcp.connect((ip_address, port_num))
            time.sleep(1)
            self._flush()
        except socket.error as e:
            logger.error(f"TCP Socket connection error : {e}")
            self.tcp.close()
            return None

    def send_command(self, command: str, ending: str = "\r\n") -> None:
        self.tcp.sendall((command + ending).encode())
        time.sleep(0.2)

    def receive_data(self, buffer_size: int = 4096) -> str:
        return self.tcp.recv(buffer_size).decode()

    def send_receive(self, command: str) -> str:
        self.send_command(command)
        return self.receive_data()

    def _flush(self) -> None:
        """Flushes the socket with residual information"""
        self.tcp.settimeout(0.1)
        try:
            while self.tcp.recv(1024):
                pass
        except socket.timeout:
            pass

        finally:
            self.tcp.settimeout(None)

    def close(self) -> None:
        try:
            self.tcp.close()
        except Exception as e:
            logger.error(f" Error while closing the tcp socket: {e}")

    def is_connected(self) -> bool:
        try:
            # send a harmless command to the socket status
            self.tcp.send(b"")  # send a byte
            return True
        except socket.error:
            return False


class TicketPurpose(str, Enum):
    UPDATE_STATUS = auto()
    UPDATE_PROGRESS = auto()
    ERROR_MESSAGE = auto()
    EXECUTION_COMPLETED = auto()


class Ticket:
    def __init__(self, ticket_type: TicketPurpose, ticket_value: str):
        self.ticket_type = ticket_type
        self.ticket_value = ticket_value


class TicketHandler:
    def __init__(self, message_queue: Queue, event_widget) -> None:
        self.message_queue = message_queue
        self.event_widget = event_widget

    def update_status(self, message) -> None:
        ticket = Ticket(ticket_type=TicketPurpose.UPDATE_STATUS, ticket_value=message)
        self.message_queue.put(item=ticket)
        self.event_widget.event_generate("<<CheckQueue>>")

    def update_progress(self, message) -> None:
        ticket = Ticket(ticket_type=TicketPurpose.UPDATE_PROGRESS, ticket_value=message)
        self.message_queue.put(item=ticket)
        self.event_widget.event_generate("<<CheckQueue>>")

    def update_error(self, message) -> None:
        ticket = Ticket(ticket_type=TicketPurpose.ERROR_MESSAGE, ticket_value=message)
        self.message_queue.put(item=ticket)
        self.event_widget.event_generate("<<CheckQueue>>")

    def update_done(self, message) -> None:
        ticket = Ticket(ticket_type=TicketPurpose.ERROR_MESSAGE, ticket_value=message)
        self.message_queue.put(item=ticket)
        self.event_widget.event_generate("<<CheckQueue>>")

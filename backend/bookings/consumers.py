import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from bookings.models import ShowSeat

class SeatMapConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for live seat map updates.
    
    URL: ws/shows/<show_id>/seats/
    
    Guarantees on connect / reconnect:
    On connect, the server immediately sends full current seat-map state (`seat_map_state`)
    so reconnected clients catch up before receiving live incremental updates (`seat_updates`).
    """
    
    async def connect(self):
        self.show_id = self.scope['url_route']['kwargs']['show_id']
        self.room_group_name = f"show_{self.show_id}_seats"

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Fetch and send full seat map state to the newly connected / reconnected client
        full_state = await self.get_full_seat_map_state(self.show_id)
        await self.send(text_data=json.dumps({
            'type': 'seat_map_state',
            'show_id': self.show_id,
            'seats': full_state
        }))

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from room group (batched updates)
    async def seat_updates(self, event):
        # Send updates to WebSocket client
        await self.send(text_data=json.dumps({
            'type': 'seat_updates',
            'updates': event['updates']
        }))

    @database_sync_to_async
    def get_full_seat_map_state(self, show_id):
        seats = ShowSeat.objects.filter(show_id=show_id).select_related('seat', 'category')
        return [
            {
                'id': str(s.id),
                'seat_id': str(s.seat.id),
                'row_name': s.seat.row_name,
                'col_number': s.seat.col_number,
                'coord_x': float(s.seat.coord_x) if s.seat.coord_x is not None else 0.0,
                'coord_y': float(s.seat.coord_y) if s.seat.coord_y is not None else 0.0,
                'category_name': s.category.name,
                'price': str(s.price),
                'status': s.status,
                'hold_expires_at': s.hold_expires_at.isoformat() if s.hold_expires_at else None
            }
            for s in seats
        ]

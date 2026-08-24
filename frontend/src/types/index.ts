export interface EventItem {
  id: string;
  title: string;
  event_type: 'movie' | 'concert';
  description: string;
  banner_url: string;
}

export interface ShowItem {
  id: string;
  event_id: string;
  event_title: string;
  event_type: 'movie' | 'concert';
  venue_id: string;
  venue_name: string;
  venue_location: string;
  start_time: string;
  end_time: string;
  total_seats: number;
  available_seats: number;
  banner_url?: string;
}

export interface SeatItem {
  id: string;
  seat_id: string;
  row_name: string;
  col_number: number;
  coord_x: number;
  coord_y: number;
  category_id: string;
  category_name: string;
  price: string;
  status: 'available' | 'held' | 'booked';
  is_held_by_me?: boolean;
  hold_expires_at: string | null;
}

export interface ActiveHold {
  showSeatId: string;
  expiresAt: string;
  seatLabel: string;
  price: string;
}

export interface BookingItem {
  id: string;
  booking_reference: string;
  show_id: string;
  event_title: string;
  event_type: string;
  venue_name: string;
  start_time: string;
  seat: {
    row_name: string;
    col_number: number;
    category_name: string;
  };
  amount: string;
  status: 'confirmed' | 'cancelled';
  email_delivery_failed: boolean;
  created_at: string;
}

export interface OrganiserRevenueSummary {
  total_seats: number;
  booked_seats: number;
  held_seats: number;
  available_seats: number;
  total_revenue: string;
  occupancy_rate_percent: number;
}

export interface WaitlistEntryItem {
  id: string;
  show_id: string;
  event_title: string;
  category_name: string;
  status: 'waiting' | 'offered' | 'expired';
  offer_expires_at: string | null;
  created_at: string;
}

export interface WSSeatUpdate {
  id?: string;
  seat_id?: string;
  status: 'available' | 'held' | 'booked';
  hold_expires_at?: string | null;
}

export interface WSMessage {
  type: 'seat_map_state' | 'seat_updates';
  show_id?: string;
  seats?: SeatItem[];
  updates?: WSSeatUpdate[];
}

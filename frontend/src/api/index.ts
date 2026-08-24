import axios from 'axios';
import type { EventItem, ShowItem, SeatItem, BookingItem, OrganiserRevenueSummary } from '../types';

let rawBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
if (rawBaseUrl && !rawBaseUrl.endsWith('/api') && !rawBaseUrl.endsWith('/api/')) {
  rawBaseUrl = rawBaseUrl.replace(/\/$/, '') + '/api';
}

const api = axios.create({
  baseURL: rawBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

export const setAuthToken = (token: string | null) => {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common['Authorization'];
  }
};

export const registerApi = async (data: any) => {
  const res = await api.post('/auth/register/', data);
  return res.data;
};

export const loginApi = async (data: any) => {
  const res = await api.post('/auth/login/', data);
  return res.data;
};

export const meApi = async () => {
  const res = await api.get('/auth/me/');
  return res.data;
};

export const getEvents = async (): Promise<EventItem[]> => {
  const res = await api.get('/events/');
  return res.data;
};

export const getShows = async (): Promise<ShowItem[]> => {
  const res = await api.get('/shows/');
  return res.data;
};

export const getShowSeats = async (showId: string): Promise<SeatItem[]> => {
  const res = await api.get(`/shows/${showId}/seats/`);
  return res.data;
};

export const holdSeatApi = async (showId: string, seatId: string) => {
  const res = await api.post(`/shows/${showId}/seats/${seatId}/hold/`, {});
  return res.data;
};

export const releaseSeatApi = async (showId: string, seatId: string) => {
  const res = await api.delete(`/shows/${showId}/seats/${seatId}/hold/`);
  return res.data;
};

export const confirmBookingApi = async (
  showId: string,
  seatId: string,
  idempotencyKey: string,
  customerDetails?: { name?: string; phone?: string; email?: string }
) => {
  const res = await api.post(
    `/shows/${showId}/seats/${seatId}/book/`,
    {
      customer_name: customerDetails?.name,
      customer_phone: customerDetails?.phone,
      customer_email: customerDetails?.email,
    },
    {
      headers: {
        'Idempotency-Key': idempotencyKey,
      },
    }
  );
  return res.data;
};

export const cancelBookingApi = async (bookingId: string) => {
  const res = await api.post(`/bookings/${bookingId}/cancel/`, {});
  return res.data;
};

export const resendBookingEmailApi = async (bookingId: string) => {
  const res = await api.post(`/bookings/${bookingId}/resend-email/`, {});
  return res.data;
};

export const getUserBookingHistory = async (): Promise<BookingItem[]> => {
  const res = await api.get(`/bookings/history/`);
  return res.data;
};

export const joinWaitlistApi = async (showId: string, categoryId: string) => {
  const res = await api.post('/waitlist/join/', {
    show_id: showId,
    category_id: categoryId,
  });
  return res.data;
};

export const getUserWaitlistApi = async () => {
  const res = await api.get(`/waitlist/`);
  return res.data;
};

export const cancelWaitlistApi = async (entryId: string) => {
  const res = await api.post(`/waitlist/${entryId}/cancel/`, {});
  return res.data;
};

export const getOrganiserRevenue = async (showId?: string): Promise<OrganiserRevenueSummary> => {
  const url = showId ? `/organiser/revenue/?show_id=${showId}` : '/organiser/revenue/';
  const res = await api.get(url);
  return res.data;
};

export const getVenuesApi = async () => {
  const res = await api.get('/admin/venues/');
  return res.data;
};

export const getSeatCategoriesApi = async () => {
  const res = await api.get('/admin/seat-categories/');
  return res.data;
};

export const createVenueApi = async (data: any) => {
  const res = await api.post('/admin/venues/', data);
  return res.data;
};

export const createEventApi = async (data: any) => {
  const res = await api.post('/events/create/', data);
  return res.data;
};

export const createShowApi = async (data: any) => {
  const res = await api.post('/shows/create/', data);
  return res.data;
};

export default api;

export const getOrganiserBookings = async (): Promise<any[]> => {
  const res = await api.get('/organiser/bookings/');
  return res.data;
};

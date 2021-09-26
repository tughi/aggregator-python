const fullDateFormat = new Intl.DateTimeFormat(window.navigator.language, { year: 'numeric', month: 'short', day: '2-digit' })
const shortDateFormat = new Intl.DateTimeFormat(window.navigator.language, { month: 'short', day: '2-digit' })
const timeFormat = new Intl.DateTimeFormat(window.navigator.language, { hour: '2-digit', minute: '2-digit' })

export const formatRelativeEntryTime = (entryTime) => {
   const now = new Date()
   const date = new Date(entryTime)
   if (now.getFullYear() !== date.getFullYear()) {
      return fullDateFormat.format(date)
   }
   if (now.getDate() === date.getDate() && now.getMonth() === date.getMonth()) {
      return timeFormat.format(date)
   }
   return shortDateFormat.format(date)
}

const dateTimeFormat = new Intl.DateTimeFormat(window.navigator.language, { year: 'numeric', month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', weekday: 'short' })

export const formatFullEntryTime = (entryTime) => {
   const date = new Date(entryTime)
   return dateTimeFormat.format(date)
}


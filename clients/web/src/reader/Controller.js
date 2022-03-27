import React, { useCallback, useContext, useEffect, useMemo, useState } from "react"
import { useSession } from "./Session"

const ControllerContext = React.createContext()

const PATH_PATTERN__FEED = new RegExp('/reader/feeds/(\\d+)')

const createSessionParams = (location) => {
   let feedId = null
   let onlyUnread = true
   let onlyStarred = false
   if (location.pathname === '/reader/starred') {
      onlyUnread = false
      onlyStarred = true
   } else {
      const match = location.pathname.match(PATH_PATTERN__FEED)
      if (match) {
         feedId = parseInt(match[1])
      }
   }

   return { revision: 1, feedId, onlyUnread, onlyStarred }
}

const currentLocation = () => ({
   pathname: window.location.pathname,
   state: window.history.state,
})

export const Controller = ({ setShowSideNav, children }) => {
   const [sessionParams, setSessionParams] = useState(() => createSessionParams(currentLocation()))
   const session = useSession(sessionParams)

   const [activeEntryIndex, setActiveEntryIndex] = useState(-1)
   const [isViewerVisible, setIsViewerVisible] = useState(false)

   useEffect(() => {
      const location = currentLocation()
      if (isViewerVisible) {
         if (!location.state?.viewer) {
            window.history.pushState({ ...location.state, viewer: true }, '', location.pathname)
         }
      } else {
         if (location.state?.viewer) {
            window.history.go(-1)
         }
      }
   }, [isViewerVisible])

   useEffect(() => {
      if (isViewerVisible) {
         if (activeEntryIndex === -1) {
            setIsViewerVisible(false)
         }
      }
   }, [activeEntryIndex, isViewerVisible])

   const refresh = useCallback(() => {
      setSessionParams(params => ({ ...params, revision: params.revision + 1 }))
   }, [setSessionParams])

   useEffect(() => {
      setIsViewerVisible(false)
      setActiveEntryIndex(-1)
   }, [sessionParams])

   useEffect(() => {
      const onKeyDown = event => {
         const key = event.which
         if (key === 66/*b*/ && activeEntryIndex !== -1) {
            // TODO: toggle bliss
         } else if (key === 74/*j*/ && session.entries.length) {
            setActiveEntryIndex(Math.min(session.entries.length - 1, activeEntryIndex + 1))
            setIsViewerVisible(true)
         } else if (key === 75/*k*/ && session.entries.length) {
            setActiveEntryIndex(Math.max(0, activeEntryIndex - 1))
            setIsViewerVisible(true)
         } else if (key === 77/*m*/ && activeEntryIndex !== -1) {
            const activeEntry = session.entries[activeEntryIndex]
            session.toggleEntryReadState(activeEntry)
         } else if (key === 78/*n*/ && session.entries.length) {
            setActiveEntryIndex(Math.min(session.entries.length - 1, activeEntryIndex + 1))
         } else if (key === 79/*o*/ && activeEntryIndex !== -1) {
            setIsViewerVisible(visible => !visible)
         } else if (key === 80/*p*/ && session.entries.length) {
            setActiveEntryIndex(Math.max(0, activeEntryIndex - 1))
         } else if (key === 82/*r*/) {
            refresh()
         } else if (key === 83/*s*/ && activeEntryIndex !== -1) {
            const activeEntry = session.entries[activeEntryIndex]
            session.toggleEntryStarState(activeEntry)
         } else if (key === 86/*v*/ && activeEntryIndex !== -1) {
            const activeEntry = session.entries[activeEntryIndex]
            window.open(activeEntry.link, '_blank', 'noopener noreferrer')

         }
      }

      window.addEventListener('keydown', onKeyDown)

      return () => {
         window.removeEventListener('keydown', onKeyDown)
      }
   }, [activeEntryIndex, session, refresh])

   const openFeed = useCallback((link, sessionParams) => {
      const location = currentLocation()
      const onPopState = () => {
         if (link === '/reader/all') {
            window.history.replaceState({ all: true }, '', link)
         } else {
            window.history.pushState({ feed: true }, '', link)
         }

         setSessionParams(params => ({ ...params, ...sessionParams, revision: session.revision + 1 }))
         setShowSideNav(false)

         window.removeEventListener('popstate', onPopState)
      }

      if (location.state?.feed && location.state?.viewer) {
         window.history.go(-2)
         window.addEventListener('popstate', onPopState)
      } else if (location.state?.feed) {
         window.history.go(-1)
         window.addEventListener('popstate', onPopState)
      } else {
         onPopState()
      }
   }, [session, setSessionParams, setShowSideNav])

   useEffect(() => {
      const onPopState = () => {
         setTimeout(() => {
            const location = currentLocation()
            const { feedId, onlyUnread, onlyStarred } = createSessionParams(location)
            setSessionParams(params => {
               if (feedId !== params.feedId || onlyUnread !== params.onlyUnread || onlyStarred !== params.onlyStarred) {
                  return { ...params, revision: params.revision + 1, feedId, onlyUnread, onlyStarred }
               }
               return params
            })

            setIsViewerVisible(!!location.state?.viewer)
         }, 0)
      }

      window.addEventListener('popstate', onPopState)

      return () => {
         window.removeEventListener('popstate', onPopState)
      }
   }, [setSessionParams])

   const toggleSortOrder = useCallback(() => {
      setSessionParams(params => ({ ...params, latestFirst: !params.latestFirst }))
   }, [])

   const toggleMaxAge = useCallback(() => {
      setSessionParams(params => {
         let { maxAge } = params
         if (maxAge === 1) {
            maxAge = 7
         } else if (maxAge === 7) {
            maxAge = null
         } else {
            maxAge = 1
         }
         return { ...params, maxAge }
      })
   }, [])

   const controller = useMemo(
      () => ({
         activeEntryIndex, setActiveEntryIndex, isViewerVisible, setIsViewerVisible, setShowSideNav, openFeed, session, refresh, toggleSortOrder, toggleMaxAge
      }),
      [
         activeEntryIndex, setActiveEntryIndex, isViewerVisible, setIsViewerVisible, setShowSideNav, openFeed, session, refresh, toggleSortOrder, toggleMaxAge
      ]
   )

   return (
      <ControllerContext.Provider value={controller}>
         {children}
      </ControllerContext.Provider>
   )
}

export const useController = () => useContext(ControllerContext)

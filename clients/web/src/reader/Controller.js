import React, { useCallback, useContext, useEffect, useMemo, useState } from "react"
import { matchPath, useHistory } from "react-router"
import { useSession } from "./Session"

const ControllerContext = React.createContext()

const createSessionParams = location => {
   let feedId = null
   let onlyUnread = true
   let onlyStarred = false
   if (location.pathname === '/reader/starred') {
      onlyUnread = false
      onlyStarred = true
   } else {
      const match = matchPath(location.pathname, { path: '/reader/feeds/:feedId' })
      if (match) {
         feedId = parseInt(match.params.feedId)
      }
   }

   return { revision: 1, feedId, onlyUnread, onlyStarred }
}

export const Controller = ({ setShowSideNav, children }) => {
   const history = useHistory()
   const location = history.location

   const [sessionParams, setSessionParams] = useState(() => createSessionParams(location))
   const session = useSession(sessionParams)

   const [activeEntryIndex, setActiveEntryIndex] = useState(-1)
   const [isViewerVisible, setIsViewerVisible] = useState(false)

   useEffect(() => {
      const location = history.location
      if (isViewerVisible) {
         if (!location.state?.viewer) {
            history.push(location.pathname, { ...location.state, viewer: true })
         }
      } else {
         if (location.state?.viewer) {
            history.go(-1)
         }
      }
   }, [history, isViewerVisible])

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
            if (activeEntry.keepTime) {
               session.readEntry(activeEntry)
            } else {
               session.keepEntry(activeEntry)
            }
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
            if (activeEntry.starTime) {
               session.unstarEntry(activeEntry)
            } else {
               session.starEntry(activeEntry)
            }
         }
      }

      window.addEventListener('keydown', onKeyDown)

      return () => {
         window.removeEventListener('keydown', onKeyDown)
      }
   }, [activeEntryIndex, session, refresh])

   const openFeed = useCallback((link, sessionParams) => {
      const location = history.location

      const onPopState = () => {
         if (link === '/reader/all') {
            history.replace(link, { all: true })
         } else {
            history.push(link, { feed: true })
         }

         setSessionParams({ ...sessionParams, revision: session.revision + 1 })
         setShowSideNav(false)

         window.removeEventListener('popstate', onPopState)
      }

      if (location.state?.feed && location.state?.viewer) {
         history.go(-2)
         window.addEventListener('popstate', onPopState)
      } else if (location.state?.feed) {
         history.go(-1)
         window.addEventListener('popstate', onPopState)
      } else {
         onPopState()
      }
   }, [history, session, setSessionParams, setShowSideNav])

   useEffect(() => {
      const onPopState = () => {
         setTimeout(() => {
            const location = history.location
            const { feedId, onlyUnread, onlyStarred } = createSessionParams(location)
            setSessionParams(params => {
               if (feedId !== params.feedId || onlyUnread !== params.onlyUnread || onlyStarred !== params.onlyStarred) {
                  return { revision: params.revision + 1, feedId, onlyUnread, onlyStarred }
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
   }, [history, setSessionParams])

   const toggleSortOrder = useCallback(() => {
      setSessionParams(params => ({ ...params, latestFirst: !params.latestFirst }))
   }, [])

   const controller = useMemo(
      () => ({
         activeEntryIndex, setActiveEntryIndex, isViewerVisible, setIsViewerVisible, setShowSideNav, openFeed, session, refresh, toggleSortOrder
      }),
      [
         activeEntryIndex, setActiveEntryIndex, isViewerVisible, setIsViewerVisible, setShowSideNav, openFeed, session, refresh, toggleSortOrder
      ]
   )

   return (
      <ControllerContext.Provider value={controller}>
         {children}
      </ControllerContext.Provider>
   )
}

export const useController = () => useContext(ControllerContext)
